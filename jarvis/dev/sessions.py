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

import logging
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path

from jarvis.dev.sessions_model import (  # noqa: F401 (DESCRICAO e Session também são pegos de fora)
    AGUARDANDO,
    DESCRICAO,
    ESPERANDO,
    RECENT_SECONDS,
    Session,
    claude_home,
)
from jarvis.dev.sessions_parse import (  # noqa: F401 (read_tail também é pego de fora)
    Tail,
    _claude_alive,
    _state,
    parse_tail,
    read_roster,
    read_tail,
)

log = logging.getLogger(__name__)


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
