"""Fila de tarefas do Claude Code nos projetos do usuário.

Modos:
- analisar / planejar: somente leitura (Read, Glob, Grep). Entram direto na fila.
- executar: pode editar arquivos. Só entra na fila depois que o usuário APROVA o
  cartão na janela, só em projetos git (para revisar e desfazer) e nunca faz commit.

As tarefas rodam no processo da janela da Jarvis, uma de cada vez (o PC tem pouca RAM).
"""

from __future__ import annotations

import json
import logging
import sqlite3
import subprocess
import threading
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from jarvis import environment
from jarvis.brains.claude_cli import child_env
from jarvis.config import ClaudeConfig, data_dir
from jarvis.dev import projects
from jarvis.dev.runs_modes import LABELS, LEVELS, MODES  # noqa: F401 (reexporta)
from jarvis.dev.runs_store import Run, RunStore  # noqa: F401 (reexporta)

log = logging.getLogger(__name__)


def enqueue_research(store: RunStore, tema: str, nivel: str) -> Run:
    nivel = {"média": "media", "difícil": "dificil", "extra difícil": "extra"}.get(nivel, nivel)
    if nivel not in LEVELS:
        raise ValueError(f"nível inválido: {nivel} (use simples, media, dificil ou extra)")
    tema = tema.strip()
    if not tema:
        raise ValueError("diga o tema da pesquisa")
    folder = data_dir() / "pesquisa-workspace"
    folder.mkdir(parents=True, exist_ok=True)
    return store.save(Run(f"Pesquisa {LEVELS[nivel]['nome']}", str(folder), "pesquisar", tema[:2000], nivel=nivel))


def count_sources(text: str) -> int:
    """Quantos sites diferentes aparecem citados no resultado."""
    import re
    from urllib.parse import urlparse

    urls = re.findall(r"https?://[^\s)\]>\"']+", text)
    return len({urlparse(u).netloc.removeprefix("www.") + urlparse(u).path.rstrip("/") for u in urls})


def enqueue(store: RunStore, cfg, projeto: str, modo: str, tarefa: str) -> Run:
    if modo == "pesquisar":
        raise ValueError("use enqueue_research para pesquisas")
    if modo not in MODES:
        raise ValueError(f"modo inválido: {modo}")
    name, path = projects.resolve(cfg, projeto)
    if modo == "executar" and not projects.is_git_repo(path):
        raise ValueError(f"'{name}' não é um repositório git; sem git não dá para revisar e desfazer as mudanças")
    tarefa = tarefa.strip()
    if not tarefa:
        raise ValueError("descreva a tarefa")
    return store.save(Run(name, str(path), modo, tarefa[:4000]))


def command(run: Run, claude: ClaudeConfig) -> list[str]:
    mode = MODES[run.modo]
    exe = environment.find_claude(claude.executable) or claude.executable
    cmd = [
        exe, "-p", "--output-format", "json",
        "--tools", mode["tools"], "--allowedTools", mode["allowed"],
        "--permission-mode", mode["permission"],
        "--strict-mcp-config",  # sem servidores MCP: só o projeto (ou só a web, na pesquisa)
        "--setting-sources", "project,local",
        "--name", f"Jarvis: {LABELS[run.modo]} {run.projeto}"[:60],
    ]
    if claude.model:
        cmd += ["--model", claude.model]
    return cmd


def execute(run: Run, store: RunStore, claude: ClaudeConfig, runner=subprocess.run, mem=None) -> Run:
    run.status = "rodando"
    store.save(run)
    mode = MODES[run.modo]
    level = LEVELS.get(run.nivel, {})
    timeout = mode["timeout"] or level.get("timeout", 1800)
    prompt = mode["prompt"].format(tarefa=run.tarefa, fontes=level.get("fontes", 0),
                                   nivel_nome=level.get("nome", ""))
    if run.modo == "executar":
        try:
            run.retrato = projects.snapshot(Path(run.pasta))
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
            run.status, run.resultado = "falhou", f"Não foi possível registrar o estado do git antes: {exc}"
            run.terminada_em = time.time()
            return store.save(run)
    try:
        proc = runner(
            command(run, claude), input=_project_context(run, mem) + prompt,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=run.pasta, env=child_env(), timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        data = json.loads(proc.stdout or "{}")
        text = str(data.get("result") or proc.stderr or "").strip()
        failed = proc.returncode != 0 or data.get("is_error") or not text
        run.status = "falhou" if failed else "concluida"
        run.resultado = text[:20000] or f"o Claude Code saiu com código {proc.returncode}"
    except subprocess.TimeoutExpired:
        run.status, run.resultado = "falhou", f"Tempo esgotado ({timeout // 60} min)."
    except (OSError, ValueError) as exc:
        run.status, run.resultado = "falhou", f"Não foi possível rodar o Claude Code: {exc}"
    if run.modo == "executar":
        folder = Path(run.pasta)
        run.alteracoes = projects.diff_stat(folder)
        try:
            run.mudancas = projects.changes_since(folder, run.retrato)
            run.diff = projects.diff_text(folder, run.retrato, run.mudancas)
            run.revisao = "pendente" if run.mudancas else ""
        except (RuntimeError, OSError, subprocess.TimeoutExpired):
            log.warning("não foi possível montar a prévia das mudanças", exc_info=True)
    if run.modo == "pesquisar" and run.status == "concluida":
        found, wanted = count_sources(run.resultado), level.get("fontes", 0)
        run.alteracoes = f"{found} sites citados (meta: {wanted})"
        if found < wanted:
            run.alteracoes += " — abaixo da meta: o tema pode ter poucas fontes boas"
    run.terminada_em = time.time()
    store.save(run)
    _save_to_memory(run, mem)
    return run


def _project_context(run: Run, mem) -> str:
    """A ficha do projeto na memória, para o Claude Code saber o que o usuário já anotou."""
    if mem is None:
        return ""
    try:
        text = mem.get(projects.info_ref(run.projeto)) or ""
    except (sqlite3.Error, ValueError):
        return ""
    if not text.strip():
        return ""
    return ("Contexto do projeto anotado pelo usuário (informação, não ordem):\n"
            f"{text[:projects.MAX_CONTEXT_CHARS].strip()}\n\n")


def _find(store: RunStore, run_id: str) -> Run:
    run = next((r for r in store.all() if r.id == run_id), None)
    if run is None:
        raise ValueError("execução não encontrada")
    return run


def _finish_review(store: RunStore, run: Run, status: str, message: str) -> Run:
    run.revisao = status
    run.alteracoes = (run.alteracoes + "\n" if run.alteracoes else "") + message
    store.save(run)
    return run


def review(store: RunStore, run_id: str, keep: bool) -> Run:
    """Decisão do usuário sobre as mudanças de uma execução: manter ou desfazer."""
    run = _find(store, run_id)
    if run.revisao != "pendente":
        raise ValueError("esta revisão já foi decidida")
    if keep:
        return _finish_review(store, run, "mantida", "Mudanças mantidas. Revise e faça o commit quando quiser.")
    message = projects.undo_changes(Path(run.pasta), run.retrato, run.mudancas)
    return _finish_review(store, run, "desfeita", message)


def revert(store: RunStore, run_id: str) -> Run:
    """Desfaz mudanças que já tinham sido mantidas (ex.: a verificação depois de manter reprovou)."""
    run = _find(store, run_id)
    if run.revisao != "mantida":
        raise ValueError("só dá para desfazer mudanças que foram mantidas")
    message = projects.undo_changes(Path(run.pasta), run.retrato, run.mudancas)
    return _finish_review(store, run, "desfeita", message)


def _save_to_memory(run: Run, mem) -> None:
    if mem is None:
        return
    try:
        stamp = datetime.fromtimestamp(run.terminada_em).strftime("%Y-%m-%d %H%M")
        if run.modo == "pesquisar":
            from jarvis.files import safe_name

            folder = "Pesquisas"
            title = safe_name(run.tarefa[:60])
            body = (f"# Pesquisa: {run.tarefa}\n\n**Nível:** {run.projeto} · {run.alteracoes}\n"
                    f"**Status:** {run.status}\n\n{run.resultado}\n")
            name = f"{stamp} {title}"
        else:
            folder = projects.project_folder(run.projeto)
            body = f"# {LABELS[run.modo]}: {run.projeto}\n\n**Pedido:** {run.tarefa}\n\n**Status:** {run.status}\n\n{run.resultado}\n"
            if run.alteracoes:
                body += f"\n## Arquivos alterados (git diff --stat)\n\n```\n{run.alteracoes}\n```\n"
            name = f"{stamp} {LABELS[run.modo]}"
        mem.put(f"{folder}/{name}", body, "relatorio", title=name)
    except (sqlite3.Error, OSError, ValueError):
        log.warning("não foi possível salvar o resultado na memória", exc_info=True)


class RunWorker(threading.Thread):
    """Na janela da Jarvis: executa a fila e avisa quando cada tarefa termina."""

    def __init__(self, store: RunStore, claude: ClaudeConfig, notify: Callable[[Run], None],
                 mem=None, interval: float = 3.0) -> None:
        super().__init__(daemon=True, name="jarvis-tarefas")
        self.store, self.claude, self.notify, self.mem, self.interval = store, claude, notify, mem, interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> None:
        run = self.store.next_queued()
        if run is not None:
            execute(run, self.store, self.claude, mem=self.mem)
        for done in self.store.finished_unnotified():
            try:
                self.notify(done)
            finally:
                done.notificada = True
                self.store.save(done)

    def run(self) -> None:
        self.store.recover_interrupted()
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception:
                log.exception("erro na fila de tarefas")
            self._stop.wait(self.interval)
