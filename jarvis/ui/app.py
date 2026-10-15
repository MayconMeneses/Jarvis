"""Janela de chat (pywebview) + ícone na bandeja.

Fechar a janela só a esconde; para encerrar, use "Sair" no ícone da bandeja.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

import webview

from jarvis import briefing, config, memory
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
        self._voice = None  # VoiceLoop, quando a voz está ativa
        self._vault = memory.open_vault(cfg.obsidian_vault)

    def _diary(self, entry: str) -> None:
        if self._vault is not None:
            try:
                self._vault.diary(entry)
            except OSError:
                log.warning("não foi possível escrever no diário", exc_info=True)

    def greeting(self) -> str:
        """Saudação + clima (+ manchetes na 1ª abertura do dia), também falada."""
        try:
            result = briefing.build(config.load())
        except Exception:
            log.exception("falha no briefing")
            return f"Olá, {self._cfg.user_name}! Como você está?"
        self._conversation.remember_said(result["text"])
        if self._voice is not None:
            threading.Thread(target=self._voice.speak, args=(result["speak"],), daemon=True).start()
        return result["text"]

    def open_link(self, url: str) -> bool:
        """Abre no navegador padrão. Só http(s): nada de file:, javascript: etc."""
        url = str(url)
        if not url.startswith(("https://", "http://")):
            return False
        import webbrowser

        return webbrowser.open(url)

    def voice_available(self) -> bool:
        return self._voice is not None

    def listen_now(self) -> None:
        if self._voice is not None:
            self._voice.listen_now()

    def send(self, text: str) -> dict:
        started = time.time()
        self._diary(f"Pedido: {text}")
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
        self._diary(f"Ação {action.status}: {action.descricao} {action.resultado}")
        self._conversation.note(f"Ação '{action.descricao}' {action.status}. {action.resultado}")
        return {"status": action.status, "resultado": action.resultado}

    def reset(self) -> None:
        self._conversation.reset()


def build_voice(cfg: Config, api: Api, window):
    from jarvis.voice.loop import VoiceLoop
    from jarvis.voice.stt import Transcriber
    from jarvis.voice.tts import Speaker

    def notify(payload: dict) -> None:
        try:
            window.evaluate_js(f"window.onVoice({json.dumps(payload, ensure_ascii=False)})")
        except Exception:  # janela fechando
            log.debug("não foi possível atualizar a janela", exc_info=True)

    return VoiceLoop(
        respond=api.send,
        notify=notify,
        speaker=Speaker(cfg.voz.voz),
        transcriber=Transcriber(cfg.voz.modelo_transcricao, cfg.user_name),
        sensitivity=cfg.voz.sensibilidade,
        speak_answers=cfg.voz.falar_respostas,
    )


def build_task_worker(cfg: Config, api: Api, window):
    from jarvis.dev import runs

    def notify(run) -> None:
        label = runs.LABELS[run.modo]
        ok = run.status == "concluida"
        head = f"{'✅' if ok else '⚠️'} {label} do projeto {run.projeto} {'concluída' if ok else 'falhou'}"
        body = f"{head}:\n{run.resultado}"
        if run.alteracoes:
            body += f"\n\nArquivos alterados:\n{run.alteracoes}"
        api._conversation.note(f"{head}. Pedido: {run.tarefa[:200]}. Resultado: {run.resultado[:2000]}")
        api._diary(f"{head}: {run.tarefa[:120]}")
        try:
            window.evaluate_js(f"window.onVoice({json.dumps({'task': body}, ensure_ascii=False)})")
        except Exception:
            log.debug("janela indisponível para o aviso da tarefa", exc_info=True)
        if api._voice is not None:
            api._voice.speak(f"{head}. Os detalhes estão na janela.")

    return runs.RunWorker(runs.RunStore(), cfg.claude, notify, vault=api._vault)


def run(cfg: Config, conversation: Conversation) -> int:
    api = Api(cfg, conversation)
    window = webview.create_window(
        "Jarvis",
        html=HTML.read_text(encoding="utf-8"),
        js_api=api,
        width=440,
        height=680,
        min_size=(360, 480),
    )
    quitting = False
    voice = build_voice(cfg, api, window) if cfg.voz.ativa else None
    api._voice = voice
    tasks = build_task_worker(cfg, api, window)

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
        icon.stop()
        window.destroy()

    def talk_now() -> None:
        window.show()
        api.listen_now()

    icon = tray.create(on_open=window.show, on_quit=quit_app, voice=voice, on_talk=talk_now)
    window.events.closing += on_closing

    def on_started() -> None:
        icon.run_detached()
        tasks.start()
        if voice is not None:
            voice.start()

    webview.start(on_started)
    return 0
