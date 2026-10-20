"""Cérebro Claude com sessão sempre aberta (`claude -p` em modo stream-json).

Abrir um `claude -p` por pergunta custava ~11 s só de inicialização. Aqui um único
processo fica aberto e recebe as mensagens pela entrada padrão: ~2 s numa resposta
simples. Continua usando a assinatura (sem chave de API, ver child_env).

A sessão guarda o próprio histórico. A cada pergunta, só é enviado o que é novo
desde a última resposta (pergunta do usuário e registros, como ações aprovadas).
Se a conversa foi zerada, o processo morreu ou as instruções mudaram, a sessão é
reiniciada e recebe o histórico como transcrição.
"""

from __future__ import annotations

import json
import logging
import queue
import subprocess
import threading
from datetime import datetime
from pathlib import Path

from jarvis import environment
from jarvis.brains.base import Answer, BrainUnavailable, Message
from jarvis.brains.claude_cli import child_env, render_prompt
from jarvis.config import ClaudeConfig, data_dir

log = logging.getLogger(__name__)
_EOF = object()
WEB_TOOLS = "WebSearch,WebFetch"


def render_new(new: list[Message]) -> str:
    """Mensagens novas para uma sessão que já tem o histórico anterior."""
    *context, current = new
    now = f"[Agora: {datetime.now():%d/%m/%Y %H:%M}]"
    if not context:
        return f"{now}\n{current['content']}"
    who = {"user": "Usuário", "assistant": "Jarvis"}
    notes = "\n".join(f"- {who[m['role']]}: {m['content']}" for m in context)
    return f"{now}\nDesde a sua última resposta:\n{notes}\n\nMensagem do usuário:\n{current['content']}"


class ClaudeSession:
    name = "claude"

    def __init__(self, cfg: ClaudeConfig, workdir: Path | None = None,
                 mcp_config: Path | None = None, popen=subprocess.Popen) -> None:
        self.cfg = cfg
        self.workdir = workdir or data_dir() / "claude-workspace"
        self.mcp_config = mcp_config
        self._popen = popen
        self._proc = None
        self._lines: queue.Queue = queue.Queue()
        self._system: str | None = None
        self._last_seen: Message | None = None
        self._lock = threading.Lock()

    # ── processo ─────────────────────────────────────────────────────────
    def command(self, system: str) -> list[str]:
        exe = environment.find_claude(self.cfg.executable) or self.cfg.executable
        cmd = [
            exe, "-p",
            "--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
            # Só pesquisa e leitura de sites; nada de Bash/Edit na conversa.
            "--tools", WEB_TOOLS if self.cfg.web else "",
            "--strict-mcp-config",
            "--setting-sources", "project",
            "--no-session-persistence",
            "--system-prompt", system,
        ]
        allowed = [WEB_TOOLS] if self.cfg.web else []
        if self.mcp_config:
            cmd += ["--mcp-config", str(self.mcp_config)]
            allowed.append("mcp__jarvis")
        if allowed:
            cmd += ["--allowedTools", ",".join(allowed)]
        if self.cfg.model:
            cmd += ["--model", self.cfg.model]
        return cmd

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _start(self, system: str) -> None:
        self.stop()
        self.workdir.mkdir(parents=True, exist_ok=True)
        try:
            self._proc = self._popen(
                self.command(system), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                cwd=self.workdir, env=child_env(), bufsize=1,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except FileNotFoundError as exc:
            raise BrainUnavailable("Claude Code não está instalado ou fora do PATH") from exc
        self._system, self._last_seen = system, None
        self._lines = queue.Queue()
        threading.Thread(target=self._pump, args=(self._proc, self._lines), daemon=True).start()
        threading.Thread(target=self._drain_stderr, args=(self._proc,), daemon=True).start()

    @staticmethod
    def _pump(proc, lines: queue.Queue) -> None:
        for line in proc.stdout:
            lines.put(line)
        lines.put(_EOF)

    @staticmethod
    def _drain_stderr(proc) -> None:
        for line in proc.stderr:
            if line.strip():
                log.debug("claude stderr: %s", line.strip()[:300])

    def warm_up(self, system: str) -> None:
        """Abre o processo e faz um turno mínimo antes da primeira pergunta.

        O Claude Code só termina de inicializar (incluindo o servidor de ferramentas)
        ao receber a primeira mensagem; sem isso, a 1ª pergunta real levava ~6 s a mais.
        A sessão continua tratada como nova: a 1ª pergunta leva o histórico completo.
        """
        with self._lock:
            if self._alive():
                return
            self._start(system)
            try:
                self._turn("Mensagem automática de inicialização. Responda apenas: ok")
            except BrainUnavailable as exc:
                log.info("aquecimento do Claude falhou: %s", exc)
            self._last_seen = None

    def stop(self) -> None:
        proc, self._proc = self._proc, None
        if proc is not None and proc.poll() is None:
            try:
                proc.stdin.close()
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    # ── perguntas ────────────────────────────────────────────────────────
    def _pending(self, messages: list[Message]) -> list[Message] | None:
        """O que a sessão ainda não viu; None se ela precisa recomeçar do zero."""
        if self._last_seen is None:
            return None
        for i in range(len(messages) - 1, -1, -1):
            if messages[i] == self._last_seen:
                return messages[i + 1:]
        return None

    def ask(self, messages: list[Message], system: str) -> Answer:
        with self._lock:
            new = self._pending(messages) if self._alive() and system == self._system else None
            if new is None:
                if not (self._alive() and system == self._system and self._last_seen is None):
                    self._start(system)
                text = render_new(messages) if len(messages) == 1 else (
                    f"[Agora: {datetime.now():%d/%m/%Y %H:%M}]\n" + render_prompt(messages))
            else:
                text = render_new(new)
            answer = self._turn(text)
            self._last_seen = Message(role="assistant", content=answer.text)
            return answer

    def _turn(self, text: str) -> Answer:
        payload = {"type": "user", "message": {"role": "user", "content": text}}
        try:
            self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        except (OSError, ValueError) as exc:
            self.stop()
            raise BrainUnavailable("a sessão do Claude foi encerrada; tente de novo") from exc

        while True:
            try:
                line = self._lines.get(timeout=self.cfg.timeout_seconds)
            except queue.Empty:
                self.stop()
                raise BrainUnavailable("Claude demorou demais para responder") from None
            if line is _EOF:
                self.stop()
                raise BrainUnavailable("a sessão do Claude foi encerrada; tente de novo")
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") != "result":
                continue
            result = str(event.get("result") or "").strip()
            if event.get("is_error") or not result:
                log.warning("sessão do Claude retornou erro: %s", result[:300])
                raise BrainUnavailable(f"Claude indisponível: {result[:300] or 'resposta vazia'}")
            return self._com_uso(result, event)

    def _com_uso(self, texto: str, evento: dict) -> Answer:
        """Anexa tokens e custo do evento `result`. O custo da sessão é cumulativo: guarda só o que este turno somou."""
        from jarvis.uso import normaliza

        total = evento.get("total_cost_usd")
        custo = None
        if isinstance(total, (int, float)):
            anterior = getattr(self, "_custo_total", 0.0)
            custo = total - anterior if total >= anterior else total
            self._custo_total = float(total)
        return Answer(text=texto, brain="claude", usage=normaliza.do_claude(evento.get("usage")), custo_usd=custo,
                      modelo=normaliza.modelo_principal(evento.get("modelUsage")))
