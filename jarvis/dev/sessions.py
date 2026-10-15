"""Monitor das sessões do Claude Code no PC: quais estão esperando o usuário.

SOMENTE LEITURA: nunca escreve, renomeia ou apaga arquivos do Claude Code.

O formato não é documentado oficialmente. O que foi verificado no PC (Claude Code
2.1.295, outubro de 2026):

CONFIRMADO
- `~/.claude/sessions/<pid>.json`: uma ficha por processo `claude` vivo, com
  `sessionId`, `cwd`, `name`, `entrypoint` e `status` ("busy" | "idle" | "waiting").
  Com "waiting", `waitingFor` diz o motivo ("dialog open", "input needed",
  "permission prompt", "sandbox request"...). Visto no código do próprio executável.
- `~/.claude/projects/<pasta>/<sessionId>.jsonl`: o transcrito, uma linha JSON por
  evento. Mensagens têm `type` "assistant" ou "user"; blocos `tool_use` do assistente
  ficam pendentes até chegar um `tool_result` com o mesmo `tool_use_id`. A resposta
  final do turno tem `stop_reason` "end_turn". Títulos vêm em `agent-name`,
  `custom-title` e `ai-title`; `entrypoint` "sdk-cli" marca execuções `claude -p`.

HEURÍSTICA (pode errar)
- Ferramenta pendente há mais de STALE_SECONDS com a ficha "busy": provável pedido de
  permissão (no app desktop a ficha pode continuar "busy" enquanto pede), mas também
  pode ser um comando demorado.
- AskUserQuestion/ExitPlanMode pendentes: pergunta ao usuário.
- Turno encerrado cuja última frase termina em "?": pergunta; senão, só aguardando.
- Sem ficha (Claude Code antigo ou outra pasta de configuração): só o transcrito.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

TAIL_BYTES = 64 * 1024     # títulos e últimos eventos ficam sempre perto do fim
RECENT_SECONDS = 30 * 60   # transcrito sem processo vivo: só se mexeu há pouco
STALE_SECONDS = 60         # ferramenta parada há mais que isso: talvez permissão
QUESTION_TOOLS = ("AskUserQuestion", "ExitPlanMode")
LONG_TOOLS = ("Agent", "Task")  # subagentes demoram por natureza: não contam como espera

# Estados
PERMISSAO = "permissao"    # pedido de permissão ou diálogo aberto
PERGUNTA = "pergunta"      # pergunta ao usuário
AGUARDANDO = "aguardando"  # turno encerrado, esperando a próxima mensagem
TRABALHANDO = "trabalhando"
NOVA = "nova"              # aberta, mas ainda sem conversa
DESCONHECIDO = "desconhecido"
ESPERANDO = (PERMISSAO, PERGUNTA, AGUARDANDO)

DESCRICAO = {
    PERMISSAO: "esperando sua permissão",
    PERGUNTA: "com uma pergunta para você",
    AGUARDANDO: "terminou e está esperando sua resposta",
    TRABALHANDO: "trabalhando",
    NOVA: "aberta, sem conversa",
    DESCONHECIDO: "estado desconhecido",
}


def claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


@dataclass
class Session:
    session_id: str
    projeto: str
    pasta: str
    nome: str
    estado: str
    motivo: str = ""
    fonte: str = "ficha"          # "ficha" (sessions/<pid>.json) ou "transcrito" (só o .jsonl)
    atualizada_em: float = 0.0
    marca: str = ""               # muda quando começa um novo episódio de espera

    @property
    def esperando(self) -> bool:
        return self.estado in ESPERANDO

    def frase(self) -> str:
        texto = f"A sessão \"{self.nome}\" do projeto {self.projeto} está {DESCRICAO[self.estado]}"
        return texto + (f" ({self.motivo})." if self.motivo else ".")

    def to_dict(self) -> dict:
        data = asdict(self)
        data.pop("marca")
        data["descricao"] = DESCRICAO[self.estado]
        data["atualizada_em"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.atualizada_em))
        return data


# ── fichas dos processos (sessions/<pid>.json) ───────────────────────────

def _claude_alive(pid) -> bool:
    """O processo existe e é um claude (a ficha pode sobrar de um PID reaproveitado).

    Não usa os.kill(pid, 0): no Windows o sinal 0 é CTRL_C_EVENT.
    """
    import psutil

    try:
        return psutil.Process(int(pid)).name().lower().startswith("claude")
    except (psutil.Error, TypeError, ValueError):
        return False


def read_roster(home: Path, alive: Callable[[int], bool] = _claude_alive) -> dict[str, dict]:
    """sessionId → ficha mais recente entre os processos vivos."""
    found: dict[str, dict] = {}
    try:
        files = list((home / "sessions").glob("*.json"))
    except OSError:
        return found
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sid, pid = str(data["sessionId"]), int(data["pid"])
        except (OSError, ValueError, KeyError, TypeError):
            continue  # ilegível ou pega no meio da escrita
        if not alive(pid):
            continue
        old = found.get(sid)
        if old is None or (data.get("statusUpdatedAt") or 0) > (old.get("statusUpdatedAt") or 0):
            found[sid] = data
    return found


# ── transcritos (projects/<pasta>/<sessionId>.jsonl) ─────────────────────

@dataclass
class Tail:
    """O que interessa do fim do transcrito."""
    cwd: str = ""
    titulo: str = ""
    entrypoint: str = ""
    conversa: bool = False        # há alguma mensagem user/assistant
    pendentes: list[str] = field(default_factory=list)  # ferramentas sem resultado
    ultimo: str = ""              # "assistant" | "user" | ""
    fim_de_turno: bool = False
    texto_final: str = ""
    interrompido: bool = False
    uuid: str = ""


def read_tail(path: Path, nbytes: int = TAIL_BYTES) -> list[dict]:
    """Objetos JSON dos últimos `nbytes`. A 1ª linha (cortada) e linhas inválidas são ignoradas."""
    try:
        with open(path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - nbytes))
            if size > nbytes:
                fh.readline()
            raw = fh.read()
    except OSError:
        return []
    objs = []
    for line in raw.decode("utf-8", "replace").splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue  # linha sendo escrita agora
        if isinstance(obj, dict):
            objs.append(obj)
    return objs


def _blocks(obj: dict) -> list:
    content = (obj.get("message") or {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []


def parse_tail(objs: list[dict]) -> Tail:
    tail = Tail()
    pending: dict[str, str] = {}
    for obj in objs:
        kind = obj.get("type")
        if kind == "agent-name" and obj.get("agentName"):
            tail.titulo = str(obj["agentName"])
        elif kind == "custom-title" and obj.get("customTitle"):
            tail.titulo = str(obj["customTitle"])
        elif kind == "ai-title" and obj.get("aiTitle") and not tail.titulo:
            tail.titulo = str(obj["aiTitle"])
        if obj.get("cwd"):
            tail.cwd = str(obj["cwd"])
        if obj.get("entrypoint"):
            tail.entrypoint = str(obj["entrypoint"])
        if kind not in ("assistant", "user") or obj.get("isSidechain") or obj.get("isMeta"):
            continue
        tail.conversa, tail.ultimo, tail.uuid = True, kind, str(obj.get("uuid") or "")
        blocks = [b for b in _blocks(obj) if isinstance(b, dict)]
        if kind == "assistant":
            for b in blocks:
                if b.get("type") == "tool_use" and b.get("id"):
                    pending[b["id"]] = str(b.get("name") or "")
            stop = (obj.get("message") or {}).get("stop_reason")
            tail.fim_de_turno = stop in ("end_turn", "stop_sequence")
            texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            if texts:
                tail.texto_final = str(texts[-1])
            tail.interrompido = False
        else:
            for b in blocks:
                if b.get("type") == "tool_result":
                    pending.pop(b.get("tool_use_id"), None)
            text = " ".join(str(b.get("text", "")) for b in blocks if b.get("type") == "text")
            tail.interrompido = text.startswith("[Request interrupted")
            tail.fim_de_turno, tail.texto_final = False, ""
    tail.pendentes = list(pending.values())
    return tail


_URL = re.compile(r"\S+://\S+|\bwww\.\S+")


def looks_like_question(text: str) -> bool:
    """Termina em pergunta? Ignora "?" de URLs; aceita pergunta seguida de opções."""
    cleaned = _URL.sub(" ", text or "").rstrip()
    if not cleaned:
        return False
    return any(line.rstrip().endswith("?") for line in cleaned.splitlines()[-6:])


def _from_tail(tail: Tail, idle_seconds: float, roster_status: str | None) -> tuple[str, str]:
    """(estado, motivo) a partir do transcrito; roster_status ajusta a leitura."""
    if not tail.conversa:
        return NOVA, ""
    questions = [n for n in tail.pendentes if n in QUESTION_TOOLS]
    if questions:
        return PERGUNTA, questions[0]
    if tail.pendentes:
        waiting = [n for n in tail.pendentes if n not in LONG_TOOLS]
        if waiting and idle_seconds > STALE_SECONDS:
            return PERMISSAO, f"talvez: {waiting[0]} sem resposta há {int(idle_seconds)} s; pode ser só um comando demorado"
        return TRABALHANDO, ""
    if roster_status == "busy":
        return TRABALHANDO, ""
    if tail.ultimo == "assistant" and tail.fim_de_turno:
        if looks_like_question(tail.texto_final):
            return PERGUNTA, ""
        return AGUARDANDO, ""
    if tail.ultimo == "user" and tail.interrompido:
        return AGUARDANDO, "interrompida"
    if roster_status == "idle":
        return AGUARDANDO, ""
    return TRABALHANDO if roster_status is None else DESCONHECIDO, ""


def _state(roster: dict | None, tail: Tail, idle_seconds: float) -> tuple[str, str]:
    if roster is not None and roster.get("status") == "waiting":
        reason = str(roster.get("waitingFor") or "")
        if reason in ("input needed", "goal proposal"):
            return PERGUNTA, reason
        return PERMISSAO, reason or "diálogo aberto"
    return _from_tail(tail, idle_seconds, roster.get("status") if roster else None)


class SessionReader:
    """Lê as sessões com cache por (mtime, tamanho): só relê o fim do que mudou."""

    def __init__(self, home: Path | None = None, alive: Callable[[int], bool] = _claude_alive,
                 clock: Callable[[], float] = time.time) -> None:
        self.home = home or claude_home()
        self.alive, self.clock = alive, clock
        self._cache: dict[Path, tuple[tuple[int, int], Tail]] = {}

    def _tail(self, path: Path, stat: os.stat_result) -> Tail:
        key = (stat.st_mtime_ns, stat.st_size)
        hit = self._cache.get(path)
        if hit is None or hit[0] != key:
            hit = (key, parse_tail(read_tail(path)))
            self._cache[path] = hit
        return hit[1]

    def sessions(self) -> list[Session]:
        """Sessões com processo vivo, mais transcritos interativos mexidos há pouco."""
        now = self.clock()
        roster = read_roster(self.home, self.alive)
        result, seen = [], set()
        try:
            files = list((self.home / "projects").glob("*/*.jsonl"))
        except OSError:
            files = []
        for path in files:
            sid = path.stem
            try:
                stat = path.stat()
            except OSError:
                continue
            entry = roster.get(sid)
            if entry is None and now - stat.st_mtime > RECENT_SECONDS:
                continue
            tail = self._tail(path, stat)
            if entry is None and tail.entrypoint.startswith("sdk"):
                continue  # `claude -p` (inclusive as tarefas da própria Jarvis) não espera ninguém
            seen.add(sid)
            result.append(self._build(sid, entry, tail, stat.st_mtime, now))
        for sid, entry in roster.items():  # processo vivo ainda sem transcrito
            if sid not in seen:
                result.append(self._build(sid, entry, Tail(), 0.0, now))
        for path in [p for p in self._cache if p.stem not in seen]:
            del self._cache[path]  # não guardar transcritos que saíram da lista
        return sorted(result, key=lambda s: s.atualizada_em, reverse=True)

    def _build(self, sid: str, entry: dict | None, tail: Tail, mtime: float, now: float) -> Session:
        estado, motivo = _state(entry, tail, now - mtime if mtime else 0.0)
        entry = entry or {}
        pasta = str(entry.get("cwd") or tail.cwd)
        updated = max(mtime, (entry.get("statusUpdatedAt") or 0) / 1000)
        marca = str(entry.get("statusUpdatedAt") or "") if entry.get("status") == "waiting" else tail.uuid
        return Session(
            session_id=sid,
            projeto=_project_name(pasta),
            pasta=pasta,
            nome=str(entry.get("name") or tail.titulo or sid[:8]),
            estado=estado,
            motivo=motivo,
            fonte="ficha" if entry else "transcrito",
            atualizada_em=updated,
            marca=f"{estado}:{marca}",
        )


def _project_name(pasta: str) -> str:
    """Nome da pasta do projeto; num worktree (.claude/worktrees/x), o projeto de cima."""
    parts = Path(pasta).parts if pasta else ()
    if len(parts) >= 3 and parts[-3].lower() == ".claude" and parts[-2].lower() == "worktrees":
        parts = parts[:-3]
    return parts[-1] if parts else "desconhecido"


class SessionWatcher(threading.Thread):
    """Avisa UMA vez quando uma sessão passa a esperar o usuário.

    Na primeira leitura, sessões que já estavam só "aguardando" não são avisadas
    (seria um aviso por sessão parada a cada abertura da Jarvis); permissão e
    pergunta sim, porque travam o trabalho.
    """

    def __init__(self, notify: Callable[[Session], None], reader: SessionReader | None = None,
                 interval: float = 5.0) -> None:
        super().__init__(daemon=True, name="jarvis-sessoes")
        self.reader, self.notify, self.interval = reader or SessionReader(), notify, interval
        self._stop = threading.Event()
        self._avisadas: dict[str, str] = {}  # sessionId → marca já avisada
        self._primeira = True

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> list[Session]:
        novas = []
        current = self.reader.sessions()
        for s in current:
            if not s.esperando:
                self._avisadas.pop(s.session_id, None)
                continue
            if self._avisadas.get(s.session_id) == s.marca:
                continue
            self._avisadas[s.session_id] = s.marca
            if self._primeira and s.estado == AGUARDANDO:
                continue
            novas.append(s)
        ids = {s.session_id for s in current}
        self._avisadas = {k: v for k, v in self._avisadas.items() if k in ids}
        self._primeira = False
        for s in novas:
            try:
                self.notify(s)
            except Exception:
                log.exception("falha ao avisar sobre a sessão %s", s.session_id)
        return novas

    def run(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("erro no monitor de sessões do Claude Code")
            self._stop.wait(self.interval)
