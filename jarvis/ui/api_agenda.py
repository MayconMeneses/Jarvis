"""Ponte da janela para agenda, e-mails e Morning Digest. Só leitura: nada aqui muda agenda ou caixa de e-mail."""

from __future__ import annotations

import threading

from jarvis import briefing, config


class AgendaMixin:
    def bom_dia_agora(self) -> str:
        """Botão "Bom dia": Morning Digest completo (agenda, e-mails de ação, clima, manchetes), também falado."""
        result = briefing.build(config.load(), forcar=True)
        self._conversation.remember_said(result["text"])
        if self._voice is not None:
            threading.Thread(target=self._voice.speak, args=(result["speak"],), daemon=True).start()
        return result["text"]

    def agenda_hoje(self) -> str:
        from jarvis.agenda import servico, texto

        return texto.hoje(servico.do_dia(config.load()))

    def conectar_agenda(self, apelido: str, link: str, cor: str = "") -> dict:
        """Guarda o link iCal secreto no cofre do Windows; o config.json fica só com apelido e cor."""
        from jarvis.agenda import fontes

        cfg = config.load()
        try:
            fontes.adicionar(cfg, apelido, link, cor)
        except ValueError as exc:
            return {"ok": False, "mensagem": str(exc)}
        config.save(cfg)
        return {"ok": True, "mensagem": f"Agenda “{apelido}” conectada (somente leitura)."}

    def perfil_modelo(self, perfil: str, modelo: str | None = None) -> dict:
        from jarvis.brains import perfis

        cfg = config.load()
        try:
            perfis.definir(cfg, perfil, modelo)
        except ValueError as exc:
            return {"ok": False, "mensagem": str(exc)}
        config.save(cfg)
        return {"ok": True, "perfil": perfil, "modelo": perfis.modelo_do_perfil(cfg),
                "mensagem": "Vale a partir da próxima abertura da Jarvis."}
