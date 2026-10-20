"""Uma tarefa do Claude Code e a pasta onde ficam salvas."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from jarvis.config import data_dir


_last_stamp = 0.0
_stamp_lock = threading.Lock()


def _created_stamp() -> float:
    """time.time() estritamente crescente neste processo.

    No Windows com Python 3.11 o relógio anda de 15,6 em 15,6 ms: duas tarefas criadas
    em seguida teriam o mesmo criada_em, e a fila não saberia qual veio primeiro.
    """
    global _last_stamp
    with _stamp_lock:
        _last_stamp = max(time.time(), _last_stamp + 1e-6)
        return _last_stamp


@dataclass
class Run:
    projeto: str
    pasta: str
    modo: str
    tarefa: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    status: str = "na_fila"  # na_fila | rodando | concluida | falhou
    criada_em: float = field(default_factory=_created_stamp)
    terminada_em: float = 0.0
    resultado: str = ""
    alteracoes: str = ""
    notificada: bool = False
    nivel: str = ""  # só para pesquisas: simples | media | dificil | extra
    # Só para "executar": retrato de antes, arquivos mudados, diff e decisão do usuário.
    retrato: dict = field(default_factory=dict)
    mudancas: list = field(default_factory=list)
    diff: str = ""
    revisao: str = ""  # "" | pendente | mantida | desfeita
    usage: dict = field(default_factory=dict)  # tokens da tarefa ({in, out, cw, cw1h, cr}); o registro de uso vem dos .jsonl
    custo_usd: float = 0.0  # custo informado pelo Claude Code (equivalente em API)


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
