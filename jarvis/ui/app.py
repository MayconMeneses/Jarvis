"""Janela de chat (pywebview) + ícone na bandeja.

Fechar a janela só a esconde; para encerrar, use "Sair" no ícone da bandeja.
Aqui só a montagem: a ponte com o JavaScript está em api*.py, as tarefas em workers.py
e a posição/instância única em window.py.
"""

from __future__ import annotations

import os
import threading
import webview

from jarvis.chat import Conversation
from jarvis.config import Config
from jarvis.ui import tray, web
from jarvis.ui.api import Api
from jarvis.ui.window import claim_single_instance, show_already_open, window_geometry
from jarvis.ui.workers import build_session_watcher, build_task_worker, build_voice

RESTART_WAIT_SECONDS = 12.0  # a Jarvis nova espera a antiga fechar


def run(cfg: Config, conversation: Conversation) -> int:
    restarting = os.environ.pop("JARVIS_REINICIO", None) is not None
    instance = claim_single_instance(wait_seconds=RESTART_WAIT_SECONDS if restarting else 0.0)
    if instance is None:
        show_already_open()
        return 0
    api = Api(cfg, conversation)
    x, y, width, height = window_geometry()
    window = webview.create_window(
        "Jarvis",
        html=web.page(),
        js_api=api,
        x=x, y=y, width=width, height=height,
        min_size=(360, 480),
        background_color="#04070C",
    )
    api._window = window
    quitting = False
    voice = build_voice(cfg, api, window) if cfg.voz.ativa else None
    api._voice = voice
    tasks = build_task_worker(cfg, api, window)
    watcher = build_session_watcher(api, window)

    def on_closing() -> bool:
        if quitting:
            return True
        window.hide()
        return False  # cancela o fechamento: a Jarvis continua na bandeja

    def quit_app() -> None:
        nonlocal quitting
        quitting = True
        if voice is not None:
            voice.stop()
        tasks.stop()
        watcher.stop()
        conversation.router.stop()  # fecha a sessão do Claude
        icon.stop()
        window.destroy()

    def talk_now() -> None:
        window.show()
        api.listen_now()

    api._quit = quit_app
    icon = tray.create(on_open=window.show, on_quit=quit_app, voice=voice, on_talk=talk_now)
    window.events.closing += on_closing

    def on_started() -> None:
        # Abre a sessão do Claude já na largada: a 1ª pergunta não paga a inicialização.
        threading.Thread(target=conversation.warm_up, daemon=True, name="jarvis-aquecer").start()
        icon.run_detached()
        tasks.start()
        watcher.start()
        if voice is not None:
            voice.start()

    webview.start(on_started)
    return 0
