"""Janela de chat (pywebview) + ícone na bandeja.

Fechar a janela só a esconde; para encerrar, use "Sair" no ícone da bandeja.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import webview

from jarvis.brains import NoBrainAvailable
from jarvis.chat import Conversation
from jarvis.config import Config
from jarvis.pc import actions
from jarvis.ui import tray

log = logging.getLogger(__name__)
HTML = Path(__file__).with_name("chat.html")


class Api:
    """Métodos chamados pelo JavaScript da janela (window.pywebview.api.*).

    Atributos com "_" não são expostos ao JavaScript.
    """

    def __init__(
        self, cfg: Config, conversation: Conversation, store: actions.ActionStore | None = None
    ) -> None:
        self._cfg = cfg
        self._conversation = conversation
        self._store = store or actions.ActionStore()

    def greeting(self) -> str:
        return f"Olá, {self._cfg.user_name}! Em que posso ajudar?"

    def send(self, text: str) -> dict:
        started = time.time()
        try:
            answer = self._conversation.ask(str(text))
        except NoBrainAvailable as exc:
            return {"error": str(exc)}
        except Exception:  # a janela nunca deve travar por um erro inesperado
            log.exception("erro ao responder")
            return {"error": "Erro inesperado. Detalhes no log da Jarvis."}
        proposals = [
            {"id": a.id, "descricao": a.descricao, "motivo": a.motivo}
            for a in self._store.pending_since(started)
        ]
        return {"text": answer.text, "brain": answer.brain, "actions": proposals}

    def decide(self, action_id: str, approve: bool) -> dict:
        try:
            action = actions.decide(self._store, str(action_id), bool(approve))
        except (ValueError, FileNotFoundError) as exc:
            return {"status": "falhou", "resultado": str(exc)}
        log.info("ação %s %s: %s", action.kind, action.status, action.resultado)
        self._conversation.note(f"Ação '{action.descricao}' {action.status}. {action.resultado}")
        return {"status": action.status, "resultado": action.resultado}

    def reset(self) -> None:
        self._conversation.reset()


def run(cfg: Config, conversation: Conversation) -> int:
    window = webview.create_window(
        "Jarvis",
        html=HTML.read_text(encoding="utf-8"),
        js_api=Api(cfg, conversation),
        width=440,
        height=680,
        min_size=(360, 480),
    )
    quitting = False

    def on_closing() -> bool:
        if quitting:
            return True
        window.hide()
        return False  # cancela o fechamento: a Jarvis continua na bandeja

    def quit_app() -> None:
        nonlocal quitting
        quitting = True
        icon.stop()
        window.destroy()

    icon = tray.create(on_open=window.show, on_quit=quit_app)
    window.events.closing += on_closing
    webview.start(icon.run_detached)
    return 0
