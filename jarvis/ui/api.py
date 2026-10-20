"""Ponte entre a janela (JavaScript) e o núcleo da Jarvis.

Os métodos públicos viram window.pywebview.api.*; os que começam com "_" não são expostos.
Cada assunto vive no seu próprio módulo (mixins), para nenhum arquivo virar um "god file".
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time

from jarvis import briefing, config, files, memory_db
from jarvis.agentes.registro import registro as registro_agentes
from jarvis.brains import NoBrainAvailable
from jarvis.chat import Conversation
from jarvis.config import Config
from jarvis.pc import actions
from jarvis.ui.api_agents import AgentsMixin
from jarvis.ui.api_agenda import AgendaMixin
from jarvis.ui.api_brains import BrainsMixin
from jarvis.ui.api_files import FilesMixin
from jarvis.ui.api_learning import LearningMixin
from jarvis.ui.api_mobile import MobileMixin
from jarvis.ui.api_oficina import OficinaMixin
from jarvis.ui.api_memory import MemoryMixin
from jarvis.ui.api_review import ReviewMixin
from jarvis.ui.api_selfupdate import SelfUpdateMixin
from jarvis.ui.api_update import UpdateMixin
from jarvis.ui.api_uso import UsoMixin
from jarvis.ui.api_visual import VisualMixin

log = logging.getLogger(__name__)


class Api(AgendaMixin, FilesMixin, OficinaMixin, MobileMixin, BrainsMixin, MemoryMixin, ReviewMixin, LearningMixin, SelfUpdateMixin, UpdateMixin, VisualMixin, AgentsMixin, UsoMixin):
    """Métodos chamados pelo JavaScript da janela (window.pywebview.api.*)."""

    def __init__(
        self, cfg: Config, conversation: Conversation, store: actions.ActionStore | None = None
    ) -> None:
        self._cfg = cfg
        self._conversation = conversation
        self._store = store or actions.ActionStore()
        self._voice = None  # VoiceLoop, quando a voz está ativa
        self._ultimo_pedido = 0.0  # para o aprendizado autônomo só trabalhar com o PC parado
        self._memory = memory_db.open_memory(cfg)
        registro_agentes.ligar_memoria(self._memory)  # batimentos dos agentes ficam gravados na memória
        self._files = files.AttachmentStore()
        self._window = None  # definida em run(); usada no seletor de arquivos
        self._quit = None  # definida em run(); fecha a Jarvis (usada no reinício)

    def _diary(self, entry: str) -> None:
        try:
            self._memory.diary(entry)
        except (sqlite3.Error, OSError):
            log.warning("não foi possível escrever no diário", exc_info=True)

    def greeting(self) -> str:
        """Saudação + clima (+ manchetes na 1ª abertura do dia), também falada."""
        try:
            result = briefing.build(config.load())
            self._memory.set_meta(f"proativo:bomdia:{time.strftime('%Y-%m-%d')}", "saudacao")  # o bom dia já foi dado
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

    def system_stats(self) -> dict:
        """Números reais para os medidores do HUD (leitura leve, sem esperar)."""
        import psutil

        disk = psutil.disk_usage("C:\\")
        return {
            # Cada chamada vem de uma thread nova: interval=None sempre daria 0 na 1ª leitura.
            "cpu": round(psutil.cpu_percent(interval=0.3)),
            "ram": round(psutil.virtual_memory().percent),
            "disco": round(disk.percent),
        }

    def voice_available(self) -> bool:
        return self._voice is not None

    def listen_now(self) -> None:
        if self._voice is not None:
            self._voice.listen_now()

    def send(self, text: str, attachments: list | None = None) -> dict:
        started = self._ultimo_pedido = time.time()
        text = str(text)
        if attachments:
            listed = []
            for att_id in attachments:
                try:
                    att = self._files.get(str(att_id))
                    listed.append(f"- {att.nome} ({att.tipo}, {att.tamanho_kb} KB) — id {att.id}")
                except ValueError as exc:
                    listed.append(f"- anexo {att_id}: {exc}")
            text = (text or "Analise os arquivos anexados.") + (
                "\n\n[Arquivos anexados pelo usuário — leia com ler_anexo(id):]\n" + "\n".join(listed))
        self._diary(f"Pedido: {text[:300]}")
        try:
            answer = self._conversation.ask(text)
        except NoBrainAvailable as exc:
            self._note_idea(f"Responder mesmo quando nenhum cérebro está disponível: \"{text[:120]}\"", "falha")
            return {"error": str(exc)}
        except Exception:  # a janela nunca deve travar por um erro inesperado
            log.exception("erro ao responder")
            return {"error": "Erro inesperado. Detalhes no log da Jarvis."}
        self._memoria_viva(answer, text)  # tira a linha [[SAVE]] da tela e da voz e cria o cartão (nunca grava)
        proposals = [
            {"id": a.id, "descricao": a.descricao, "motivo": a.motivo}
            for a in self._store.pending_since(started)
        ]
        result = self._evaluate(text, answer, time.time() - started)
        self._learn_from(text, answer, result)
        return {"text": answer.text, "brain": answer.brain, "actions": proposals, "qualidade": result}

    def reset(self) -> None:
        self._conversation.reset()
