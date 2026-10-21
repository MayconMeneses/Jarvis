"""Painel "Jarvis no celular": liga o servidor do app (PWA), gera o código de pareamento e revoga aparelhos."""

from __future__ import annotations

import logging

from jarvis import config
from jarvis.mobile import tailscale

log = logging.getLogger(__name__)
AVISO_REDE = ("Conexão sem criptografia na rede local: use só em Wi-Fi de confiança. "
              "Para mais segurança, instale o Tailscale (HTTPS e acesso de qualquer lugar).")


class MobileMixin:
    _mobile = None  # ServidorCelular, quando ligado
    _pareamento = None
    mobile_modo = ""  # como o servidor está alcançável agora: tailscale | rede | local

    def _pair(self):
        from jarvis.mobile.pareamento import Pareamento

        if self._pareamento is None:
            self._pareamento = Pareamento()
        return self._pareamento

    def mobile_start(self) -> str:
        """Liga o servidor segundo a configuração. Devolve o endereço (ou levanta OSError se a porta estiver ocupada)."""
        from jarvis.mobile import leitura
        from jarvis.mobile.servidor import ServidorCelular

        cfg = config.load()
        if self._mobile is not None and self._mobile.ativo:
            return self._mobile.url
        self._mobile = ServidorCelular(self._pair(), self.send, lambda: len(self._store.pending_since(0)), cfg.user_name,
                                      leitura=leitura.montar(config.load, getattr(self, "_vivos", dict)), origem_app=cfg.celular_origem_app)
        ts = tailscale.estado() if cfg.celular_acesso in ("auto", "tailscale") else None
        self.mobile_modo = "rede" if cfg.celular_rede else "local"
        if ts and ts["ligado"]:  # de qualquer lugar: só o endereço do Tailscale, nada exposto na rede local nem na internet
            cert, chave = cfg.celular_certificado, cfg.celular_chave
            if not (cert and chave):
                try:
                    cert, chave = tailscale.certificado(ts["nome"])
                except OSError as exc:
                    log.info("celular sem HTTPS: %s", exc)
                    cert = chave = ""
            self.mobile_modo = "tailscale"
            return self._mobile.iniciar(cfg.celular_porta, False, cert, chave, host=ts["ip"], nome=ts["nome"] if cert else "")
        if cfg.celular_acesso == "tailscale":
            self._mobile = None
            raise OSError("o Tailscale não está instalado ou ligado. " + tailscale.INSTALAR)
        return self._mobile.iniciar(cfg.celular_porta, cfg.celular_rede, cfg.celular_certificado, cfg.celular_chave)

    def mobile_stop(self) -> None:
        if self._mobile is not None:
            self._mobile.parar()

    def mobile_aviso_rede(self) -> str:
        """Aviso curto quando o servidor fala HTTP puro na rede local sem Tailscale (quem está no mesmo Wi-Fi pode espiar o tráfego)."""
        ligado = bool(self._mobile and self._mobile.ativo)
        if ligado and self.mobile_modo == "rede" and not (self._mobile.url or "").startswith("https://"):
            return AVISO_REDE
        return ""

    def mobile_status(self) -> dict:
        cfg = config.load()
        return {"ligado": bool(self._mobile and self._mobile.ativo), "url": self._mobile.url if self._mobile else "",
                "aparelhos": self._pair().listar(), "modo": self.mobile_modo, "porta": cfg.celular_porta,
                "aviso_rede": self.mobile_aviso_rede()}

    def mobile_set(self, on: bool) -> dict:
        cfg = config.load()
        cfg.celular_ativo = bool(on)
        config.save(cfg)
        try:
            if on:
                url = self.mobile_start()
                dicas = {"tailscale": " Funciona de qualquer lugar (4G ou outro Wi-Fi) pelo Tailscale, com o celular também conectado a ele.",
                         "rede": " Só funciona no mesmo Wi-Fi. Para usar de qualquer lugar, instale o Tailscale (veja docs/CELULAR.md).",
                         "local": " Só neste PC."}
                return {"ok": True, "mensagem": f"Ligado. No celular, abra {url}.{dicas.get(self.mobile_modo, '')}", **self.mobile_status()}
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
