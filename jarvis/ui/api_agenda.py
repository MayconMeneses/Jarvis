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

    # ── Conectar agenda iCal e conta IMAP (nenhuma resposta leva link, senha ou usuário completo) ──
    def agenda_email_status(self) -> dict:
        """Só nomes: agendas (apelido, cor), contas IMAP (apelido, host) e os servidores IMAP permitidos."""
        from jarvis.mail import imap

        cfg = config.load()
        return {"agendas": [{"apelido": str(a.get("apelido", "")), "cor": str(a.get("cor", ""))} for a in cfg.agendas],
                "imap": [{"apelido": str(c.get("apelido", "")), "host": str(c.get("host", ""))} for c in cfg.email.imap],
                "hosts": sorted(imap.HOSTS_PERMITIDOS)}

    def testar_agenda(self, apelido: str) -> dict:
        """Baixa o link guardado no cofre e confere se é uma agenda. O link nunca volta na resposta."""
        from jarvis.agenda import fontes, ics, servico

        achada = next((a for a in fontes.links(config.load()) if a["apelido"] == str(apelido)), None)
        if achada is None:
            return {"ok": False, "mensagem": "Essa agenda não está conectada."}
        try:
            texto = servico.baixar(achada["url"])
            if "BEGIN:VCALENDAR" not in texto.upper():
                return {"ok": False, "mensagem": "O link respondeu, mas não é uma agenda iCal."}
            eventos = len(ics.ler(texto))
        except Exception as exc:  # noqa: BLE001  (a mensagem da exceção pode conter o link)
            return {"ok": False, "mensagem": servico._erro_curto(exc).capitalize() + "."}
        return {"ok": True, "mensagem": f"Agenda lida: {eventos} compromissos encontrados."}

    def remover_agenda(self, apelido: str) -> dict:
        from jarvis.agenda import fontes

        cfg = config.load()
        fontes.remover(cfg, str(apelido))
        config.save(cfg)
        return {"ok": True, "mensagem": "Agenda removida (o link foi apagado do cofre)."}

    def conectar_imap(self, apelido: str, host: str, usuario: str, senha: str) -> dict:
        """Guarda a senha de app no cofre; o config.json fica com apelido, host e usuário. A senha nunca é devolvida."""
        from jarvis.mail import imap

        cfg = config.load()
        try:
            imap.conectar(cfg, apelido, host, usuario, "".join(str(senha).split()))
        except ValueError as exc:
            return {"ok": False, "mensagem": str(exc).replace(str(senha), "***") if senha else str(exc)}
        config.save(cfg)
        return {"ok": True, "mensagem": f"Conta “{apelido}” conectada (somente leitura). Teste a conexão."}

    def testar_imap(self, apelido: str) -> dict:
        from jarvis.mail import imap
        from jarvis.mail.base import MailError

        conf = next((c for c in config.load().email.imap if c.get("apelido") == str(apelido)), None)
        if conf is None:
            return {"ok": False, "mensagem": "Essa conta não está conectada."}
        try:
            imap.ImapAccount(conf).list_recent(1, False)
        except MailError as exc:
            return {"ok": False, "mensagem": str(exc)}  # MailError já vem sem senha
        return {"ok": True, "mensagem": "Conexão funcionando: a caixa de entrada foi lida (nada foi alterado)."}

    def desconectar_imap(self, apelido: str) -> dict:
        from jarvis.mail import imap

        cfg = config.load()
        imap.desconectar(cfg, str(apelido))
        config.save(cfg)
        return {"ok": True, "mensagem": "Conta removida (a senha foi apagada do cofre)."}
