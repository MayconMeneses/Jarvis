"""Painel "Jarvis no celular": liga o servidor do app (PWA), gera o código de pareamento e revoga aparelhos."""

from __future__ import annotations

import logging

from jarvis import config

log = logging.getLogger(__name__)


class MobileMixin:
    _mobile = None  # ServidorCelular, quando ligado
    _pareamento = None

    def _pair(self):
        from jarvis.mobile.pareamento import Pareamento

        if self._pareamento is None:
            self._pareamento = Pareamento()
        return self._pareamento

    def mobile_start(self) -> str:
        """Liga o servidor segundo a configuração. Devolve o endereço (ou levanta OSError se a porta estiver ocupada)."""
        from jarvis.mobile.servidor import ServidorCelular

        cfg = config.load()
        if self._mobile is not None and self._mobile.ativo:
            return self._mobile.url
        self._mobile = ServidorCelular(self._pair(), self.send, lambda: len(self._store.pending_since(0)), cfg.user_name)
        return self._mobile.iniciar(cfg.celular_porta, cfg.celular_rede, cfg.celular_certificado, cfg.celular_chave)

    def mobile_stop(self) -> None:
        if self._mobile is not None:
            self._mobile.parar()

    def mobile_status(self) -> dict:
        cfg = config.load()
        return {"ligado": bool(self._mobile and self._mobile.ativo), "url": self._mobile.url if self._mobile else "",
                "aparelhos": self._pair().listar(), "rede": cfg.celular_rede, "porta": cfg.celular_porta}

    def mobile_set(self, on: bool) -> dict:
        cfg = config.load()
        cfg.celular_ativo = bool(on)
        config.save(cfg)
        try:
            if on:
                url = self.mobile_start()
                aviso = " Rede local: use só em Wi-Fi de casa ou no Tailscale." if url.startswith("http://") else ""
                return {"ok": True, "mensagem": f"Ligado. No celular, abra {url}.{aviso}", **self.mobile_status()}
            self.mobile_stop()
            return {"ok": True, "mensagem": "Desligado: o celular não alcança mais a Jarvis.", **self.mobile_status()}
        except OSError as exc:
            cfg.celular_ativo = False
            config.save(cfg)
            return {"ok": False, "mensagem": f"Não consegui ligar (porta {cfg.celular_porta} ocupada?): {exc}", **self.mobile_status()}

    def mobile_code(self) -> dict:
        if not (self._mobile and self._mobile.ativo):
            return {"ok": False, "mensagem": "Ligue o “Jarvis no celular” primeiro."}
        return {"ok": True, "codigo": self._pair().novo_codigo(), "mensagem": "Digite este código no celular em até 5 minutos."}

    def mobile_revoke(self, id_: str) -> dict:
        return {"ok": self._pair().revogar(str(id_)), **self.mobile_status()}
