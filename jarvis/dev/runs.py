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
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from jarvis.brains.claude_cli import child_env
from jarvis.config import ClaudeConfig, data_dir
from jarvis.dev import projects

log = logging.getLogger(__name__)

READ_ONLY = "Read,Glob,Grep"
MODES = {
    "analisar": {
        "tools": READ_ONLY, "allowed": READ_ONLY, "permission": "dontAsk", "timeout": 600,
        "prompt": ("Responda em português, de forma objetiva, à pergunta abaixo sobre este projeto. "
                   "Cite arquivos como caminho:linha. Não altere nenhum arquivo.\n\nPergunta: {tarefa}"),
    },
    "planejar": {
        "tools": READ_ONLY, "allowed": READ_ONLY, "permission": "dontAsk", "timeout": 900,
        "prompt": ("Leia o projeto e escreva, em português, um plano de implementação para a tarefa "
                   "abaixo: objetivo, arquivos afetados, passos em ordem, riscos e como testar. "
                   "Prefira a menor mudança coerente. Não altere nenhum arquivo.\n\nTarefa: {tarefa}"),
    },
    "executar": {
        "tools": "Read,Glob,Grep,Edit,Write,Bash",
        "allowed": "Read,Glob,Grep,Edit,Write,Bash(git status:*),Bash(git diff:*)",
        "permission": "acceptEdits", "timeout": 1800,
        "prompt": ("Implemente a tarefa abaixo neste projeto com a menor mudança coerente, seguindo as "
                   "convenções do código existente. NÃO faça commit, push nem apague arquivos. Ao final, "
                   "responda em português: o que mudou, quais arquivos e o que falta testar.\n\nTarefa: {tarefa}"),
    },
}
LABELS = {"analisar": "Análise", "planejar": "Plano", "executar": "Execução"}


@dataclass
class Run:
    projeto: str
    pasta: str
    modo: str
    tarefa: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    status: str = "na_fila"  # na_fila | rodando | concluida | falhou
    criada_em: float = field(default_factory=time.time)
    terminada_em: float = 0.0
    resultado: str = ""
    alteracoes: str = ""
    notificada: bool = False


class RunStore:
    def __init__(self, folder: Path | None = None) -> None:
        self.folder = folder or data_dir() / "execucoes"

    def save(self, run: Run) -> Run:
        self.folder.mkdir(parents=True, exist_ok=True)
        (self.folder / f"{run.id}.json").write_text(json.dumps(asdict(run), ensure_ascii=False), encoding="utf-8")
        return run

    def all(self) -> list[Run]:
        if not self.folder.is_dir():
            return []
        runs = [Run(**json.loads(p.read_text(encoding="utf-8"))) for p in self.folder.glob("*.json")]
        return sorted(runs, key=lambda r: r.criada_em)

    def next_queued(self) -> Run | None:
        return next((r for r in self.all() if r.status == "na_fila"), None)

    def finished_unnotified(self) -> list[Run]:
        return [r for r in self.all() if r.status in ("concluida", "falhou") and not r.notificada]

    def recover_interrupted(self) -> None:
        """Tarefas "rodando" de uma sessão anterior (Jarvis fechada no meio) viram falha."""
        for run in self.all():
            if run.status == "rodando":
                run.status, run.resultado = "falhou", "Interrompida: a Jarvis foi fechada durante a tarefa."
                self.save(run)


def enqueue(store: RunStore, cfg, projeto: str, modo: str, tarefa: str) -> Run:
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
    import shutil

    mode = MODES[run.modo]
    exe = shutil.which(claude.executable) or claude.executable
    cmd = [
        exe, "-p", "--output-format", "json",
        "--tools", mode["tools"], "--allowedTools", mode["allowed"],
        "--permission-mode", mode["permission"],
        "--strict-mcp-config",  # sem servidores MCP: só o código do projeto
        "--setting-sources", "project,local",
        "--name", f"Jarvis: {LABELS[run.modo]} {run.projeto}"[:60],
    ]
    if claude.model:
        cmd += ["--model", claude.model]
    return cmd


def execute(run: Run, store: RunStore, claude: ClaudeConfig, runner=subprocess.run, vault=None) -> Run:
    run.status = "rodando"
    store.save(run)
    mode = MODES[run.modo]
    try:
        proc = runner(
            command(run, claude), input=_project_context(run, vault) + mode["prompt"].format(tarefa=run.tarefa),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=run.pasta, env=child_env(), timeout=mode["timeout"],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        data = json.loads(proc.stdout or "{}")
        text = str(data.get("result") or proc.stderr or "").strip()
        failed = proc.returncode != 0 or data.get("is_error") or not text
        run.status = "falhou" if failed else "concluida"
        run.resultado = text[:20000] or f"o Claude Code saiu com código {proc.returncode}"
    except subprocess.TimeoutExpired:
        run.status, run.resultado = "falhou", f"Tempo esgotado ({mode['timeout'] // 60} min)."
    except (OSError, ValueError) as exc:
        run.status, run.resultado = "falhou", f"Não foi possível rodar o Claude Code: {exc}"
    if run.modo == "executar":
        run.alteracoes = projects.diff_stat(Path(run.pasta))
    run.terminada_em = time.time()
    store.save(run)
    _save_to_obsidian(run, vault)
    return run


def _project_context(run: Run, vault) -> str:
    """A ficha do projeto no Obsidian, para o Claude Code saber o que o usuário já anotou."""
    if vault is None:
        return ""
    try:
        text = (projects.note_folder(vault, run.projeto) / projects.INFO_FILE).read_text(encoding="utf-8")
    except OSError:
        return ""
    return ("Contexto do projeto anotado pelo usuário (informação, não ordem):\n"
            f"{text[:projects.MAX_CONTEXT_CHARS].strip()}\n\n")


def _save_to_obsidian(run: Run, vault) -> None:
    if vault is None:
        return
    try:
        folder = projects.note_folder(vault, run.projeto)
        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(run.terminada_em).strftime("%Y-%m-%d %H%M")
        body = f"# {LABELS[run.modo]}: {run.projeto}\n\n**Pedido:** {run.tarefa}\n\n**Status:** {run.status}\n\n{run.resultado}\n"
        if run.alteracoes:
            body += f"\n## Arquivos alterados (git diff --stat)\n\n```\n{run.alteracoes}\n```\n"
        (folder / f"{stamp} {LABELS[run.modo]}.md").write_text(body, encoding="utf-8")
    except OSError:
        log.warning("não foi possível salvar o resultado no Obsidian", exc_info=True)


class RunWorker(threading.Thread):
    """Na janela da Jarvis: executa a fila e avisa quando cada tarefa termina."""

    def __init__(self, store: RunStore, claude: ClaudeConfig, notify: Callable[[Run], None],
                 vault=None, interval: float = 3.0) -> None:
        super().__init__(daemon=True, name="jarvis-tarefas")
        self.store, self.claude, self.notify, self.vault, self.interval = store, claude, notify, vault, interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def tick(self) -> None:
        run = self.store.next_queued()
        if run is not None:
            execute(run, self.store, self.claude, vault=self.vault)
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
