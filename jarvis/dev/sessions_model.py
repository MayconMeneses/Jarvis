"""Sessões do Claude Code: estados possíveis e o dado de cada sessão (sem acesso a arquivos)."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path


TAIL_BYTES = 64 * 1024     # títulos e últimos eventos ficam sempre perto do fim


RECENT_SECONDS = 30 * 60   # transcrito sem processo vivo: só se mexeu há pouco


STALE_SECONDS = 60         # ferramenta parada há mais que isso: talvez permissão


QUESTION_TOOLS = ("AskUserQuestion", "ExitPlanMode")


LONG_TOOLS = ("Agent", "Task")  # subagentes demoram por natureza: não contam como espera


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
