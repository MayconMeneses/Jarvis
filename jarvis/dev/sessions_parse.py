"""Sessões do Claude Code: leitura das fichas e do fim do transcrito, e o estado deduzido.

SOMENTE LEITURA (ver a explicação do formato em jarvis/dev/sessions.py)."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from jarvis.dev.sessions_model import AGUARDANDO, DESCONHECIDO, LONG_TOOLS, NOVA, PERGUNTA, PERMISSAO, QUESTION_TOOLS, STALE_SECONDS, TAIL_BYTES, TRABALHANDO


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
