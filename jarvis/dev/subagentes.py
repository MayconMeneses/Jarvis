"""Subagentes do Claude Code no PC: estado, tempo e tokens. SOMENTE LEITURA.

Lê só `~/.claude/projects/<pasta>/<sessionId>/subagents/agent-<id>.jsonl` (+ `.meta.json`) e o
transcrito da sessão-mãe. NUNCA toca em `~/.claude/sessions` (lá ficam chaves) e NUNCA guarda nem
devolve texto de conversa: dos transcritos sai só número, data e nome do modelo; do `.meta.json`, só o
tipo e a descrição curta (dado de terceiros, truncado).

Formato (Claude Code 2.1.x, verificado por estrutura, sem ler conversas):
- CONFIRMADO: `stop_reason` vem vazio em todas as linhas de subagente (gravação em fluxo), então o FIM não se
  deduz do transcrito; e a mesma `message.id` repete com `output_tokens` parcial, então somar linha a linha
  INFLA: aqui cada `message.id` conta uma vez, pelo maior valor visto.
- CONFIRMADO: o fim e os totais vêm da `task-notification` que a sessão-mãe recebe (linha `attachment` /
  `queued_command` / `commandMode: task-notification`), com <task-id> (= agentId), <status> e <usage>.
  A última notificação da mesma task-id vale. <result> e <summary> são ignorados (e descartados).
- INFERIDO (rotulado): sem notificação, "rodando" = arquivo mexido há menos de RODANDO_SEGUNDOS.
- ESTIMADO (rotulado): custo = tokens x tabela de jarvis/uso/precos.py (fonte única, aproximada por família); modelo desconhecido = sem custo.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jarvis.dev.sessions_model import claude_home
from jarvis.uso import precos

RODANDO_SEGUNDOS = 60.0
JANELA_PADRAO_S = 3600.0   # só lista os que mexeram na última hora (ou ainda rodam)
MAX_LISTA = 50
MAX_TEXTO = 80
CONCLUIDO, FALHOU, PARADO, RODANDO, INATIVO = "concluido", "falhou", "parado", "rodando", "inativo"
STATUS_FINAIS = {"completed": CONCLUIDO, "failed": FALHOU, "error": FALHOU, "killed": PARADO, "stopped": PARADO,
                 "cancelled": PARADO, "canceled": PARADO}
_RE_ID = re.compile(r"<task-id>\s*([\w.-]{1,64})\s*</task-id>")
_RE_STATUS = re.compile(r"<status>\s*([\w-]{1,32})\s*</status>")
_RE_USO = {c: re.compile(rf"<{c}>\s*(\d+)\s*</{c}>") for c in ("subagent_tokens", "tool_uses", "duration_ms")}
_RE_DESCARTAR = re.compile(r"<(result|summary)>.*?</\1>", re.S)


@dataclass
class Notificacao:
    status: str = ""
    tokens: int | None = None
    ferramentas: int | None = None
    duracao_ms: int | None = None


def ler_notificacao(prompt) -> tuple[str, Notificacao] | None:
    """(task-id, dados) de um <task-notification>. Descarta <result>/<summary> ANTES de olhar qualquer tag."""
    if not isinstance(prompt, str) or "<task-notification>" not in prompt:
        return None
    limpo = _RE_DESCARTAR.sub("", prompt)
    achou = _RE_ID.search(limpo)
    if not achou:
        return None
    status = _RE_STATUS.search(limpo)
    numeros = {c: (int(m.group(1)) if (m := rx.search(limpo)) else None) for c, rx in _RE_USO.items()}
    return achou.group(1), Notificacao(status.group(1).lower() if status else "", numeros["subagent_tokens"],
                                       numeros["tool_uses"], numeros["duration_ms"])


def _epoch(texto) -> float | None:
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return None


def _inteiro(valor) -> int:
    return valor if isinstance(valor, int) and not isinstance(valor, bool) and valor > 0 else 0


class _Incremental:
    """Lê um .jsonl só do ponto onde parou (arquivos chegam a MB). Só processa linhas completas."""

    def __init__(self) -> None:
        self.offset = 0

    def novas_linhas(self, path: Path) -> list[bytes]:
        try:
            tam = path.stat().st_size
            if tam < self.offset:
                self.reiniciar()
            if tam == self.offset:
                return []
            with open(path, "rb") as fh:
                fh.seek(self.offset)
                bruto = fh.read(tam - self.offset)
        except OSError:
            return []
        fim = bruto.rfind(b"\n") + 1
        self.offset += fim
        return bruto[:fim].splitlines()

    def reiniciar(self) -> None:
        self.offset = 0


class _Notificacoes(_Incremental):
    """Notificações de fim, lidas do transcrito da sessão-mãe: task-id → última Notificacao."""

    def __init__(self) -> None:
        super().__init__()
        self.por_id: dict[str, Notificacao] = {}

    def reiniciar(self) -> None:
        super().reiniciar()
        self.por_id = {}

    def atualizar(self, path: Path) -> None:
        for linha in self.novas_linhas(path):
            if b"task-notification" not in linha:
                continue
            try:
                anexo = json.loads(linha).get("attachment")
            except (ValueError, AttributeError):
                continue
            if isinstance(anexo, dict) and anexo.get("commandMode") == "task-notification":
                lida = ler_notificacao(anexo.get("prompt"))
                if lida:
                    self.por_id[lida[0]] = lida[1]


class _Uso(_Incremental):
    """Soma de tokens do transcrito de um subagente, com cada message.id contado UMA vez (maior valor visto)."""

    def __init__(self) -> None:
        super().__init__()
        self.por_msg: dict[str, dict[str, int]] = {}
        self.primeira: float | None = None
        self.ultima: float | None = None
        self.modelo, self.pasta = "", ""

    def reiniciar(self) -> None:
        super().reiniciar()
        self.por_msg, self.primeira, self.ultima = {}, None, None

    def atualizar(self, path: Path) -> None:
        for linha in self.novas_linhas(path):
            try:
                obj = json.loads(linha)
            except ValueError:
                continue
            if isinstance(obj, dict):
                self._linha(obj)

    def _linha(self, obj: dict) -> None:
        ts = _epoch(obj.get("timestamp"))
        if ts is not None:
            self.primeira = ts if self.primeira is None else min(self.primeira, ts)
            self.ultima = ts if self.ultima is None else max(self.ultima, ts)
        if not self.pasta and isinstance(obj.get("cwd"), str):
            from jarvis.dev.sessions import _project_name

            self.pasta = _project_name(obj["cwd"])  # só o NOME do projeto, nunca o caminho
        msg = obj.get("message")
        if obj.get("type") != "assistant" or not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
            return
        if isinstance(msg.get("model"), str):
            self.modelo = msg["model"][:60]
        u = msg["usage"]
        novo = {"in": _inteiro(u.get("input_tokens")), "out": _inteiro(u.get("output_tokens")),
                "cc": _inteiro(u.get("cache_creation_input_tokens")), "cr": _inteiro(u.get("cache_read_input_tokens"))}
        chave = str(msg.get("id") or obj.get("uuid") or len(self.por_msg))
        antigo = self.por_msg.get(chave, {})
        self.por_msg[chave] = {k: max(v, antigo.get(k, 0)) for k, v in novo.items()}

    def totais(self) -> dict[str, int]:
        return {k: sum(m[k] for m in self.por_msg.values()) for k in ("in", "out", "cc", "cr")}


def custo_estimado(modelo: str, t: dict[str, int]) -> float | None:
    """US$ ESTIMADO pela tabela única de preços (uso/precos.py); None se o modelo não tem preço."""
    custo, conhecido = precos.calcular(modelo, {"in": t["in"], "out": t["out"], "cw": t["cc"], "cr": t["cr"]}, aproximar=True)
    return round(custo, 4) if conhecido else None


@dataclass
class Subagente:
    agent_id: str
    sessao: str                 # 8 primeiros caracteres do id da sessão-mãe
    projeto: str
    tipo: str
    descricao: str
    estado: str
    inferido: bool              # True quando o estado vem só do horário do arquivo (sem notificação)
    inicio: float | None
    fim: float | None
    duracao_s: float | None
    ferramentas: int | None
    tokens: dict = field(default_factory=dict)  # {tokens_in, tokens_out, cache, tokens_total, custo_usd, estimado, origem}

    def publico(self) -> dict:
        return {k: getattr(self, k) for k in ("agent_id", "sessao", "projeto", "tipo", "descricao", "estado", "inferido",
                                              "inicio", "fim", "duracao_s", "ferramentas", "tokens")}


class LeitorSubagentes:
    """Cache por arquivo (leitura incremental): chamar a cada poucos segundos é barato."""

    def __init__(self, home: Path | None = None, clock: Callable[[], float] = time.time) -> None:
        self.home, self.clock = home or claude_home(), clock
        self._uso: dict[Path, _Uso] = {}
        self._pais: dict[Path, _Notificacoes] = {}

    def listar(self, janela_s: float = JANELA_PADRAO_S, limite: int = MAX_LISTA) -> list[Subagente]:
        agora = self.clock()
        try:
            arquivos = list((self.home / "projects").glob("*/*/subagents/agent-*.jsonl"))
        except OSError:
            return []
        achados = []
        for path in arquivos:
            try:
                achados.append((path.stat().st_mtime, path))
            except OSError:
                continue
        achados.sort(key=lambda x: x[0], reverse=True)
        saida = []
        for mtime, path in achados:
            if agora - mtime > janela_s or len(saida) >= limite:
                break  # em ordem de modificação: o resto é mais antigo (nem abre o arquivo)
            saida.append(self._montar(path, mtime, agora))
        vivos = {p for _, p in achados}
        self._uso = {p: u for p, u in self._uso.items() if p in vivos}
        return saida

    def _montar(self, path: Path, mtime: float, agora: float) -> Subagente:
        agent_id = path.stem[len("agent-"):]
        sessao_dir = path.parent.parent
        pai = sessao_dir.parent / f"{sessao_dir.name}.jsonl"
        uso = self._uso.setdefault(path, _Uso())
        uso.atualizar(path)
        notif = self._pais.setdefault(pai, _Notificacoes())
        notif.atualizar(pai)
        n = notif.por_id.get(agent_id)
        meta = _ler_meta(path.with_name(f"agent-{agent_id}.meta.json"))
        estado = STATUS_FINAIS.get(n.status) if n else None
        inferido = estado is None
        if estado is None:
            estado = RODANDO if agora - mtime < RODANDO_SEGUNDOS else INATIVO
        inicio = uso.primeira
        fim = None if estado == RODANDO else uso.ultima
        if n and n.duracao_ms is not None:
            duracao = n.duracao_ms / 1000
            if inicio is not None and estado != RODANDO:
                fim = inicio + duracao
        else:
            duracao = (uso.ultima - inicio) if inicio is not None and uso.ultima is not None else None
        t = uso.totais()
        real = n is not None and n.tokens is not None
        tokens = {"tokens_in": t["in"], "tokens_out": t["out"], "cache": t["cc"] + t["cr"],
                  "tokens_total": n.tokens if real else t["in"] + t["out"],
                  "custo_usd": custo_estimado(uso.modelo, t), "estimado": True,
                  "origem": "notificacao" if real else "transcrito"}
        return Subagente(agent_id, sessao_dir.name[:8], uso.pasta or "desconhecido", str(meta.get("agentType") or "")[:MAX_TEXTO],
                         str(meta.get("description") or "")[:MAX_TEXTO], estado, inferido, inicio, fim, duracao,
                         n.ferramentas if n else None, tokens)


def _ler_meta(path: Path) -> dict:
    try:
        dados = json.loads(path.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError):
        return {}


def resumo(itens: list[Subagente]) -> dict:
    custos = [i.tokens["custo_usd"] for i in itens if i.tokens.get("custo_usd") is not None]
    return {"total": len(itens), "rodando": sum(1 for i in itens if i.estado == RODANDO),
            "concluidos": sum(1 for i in itens if i.estado == CONCLUIDO), "falhos": sum(1 for i in itens if i.estado == FALHOU),
            "tokens_total": sum(i.tokens.get("tokens_total", 0) for i in itens),
            "custo_usd": round(sum(custos), 4) if custos else None, "estimado": True}
