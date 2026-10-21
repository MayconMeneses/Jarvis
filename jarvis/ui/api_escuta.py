"""Microfone do modo foco: estado, liga/desliga com um clique e escuta automática ao entrar no foco.

Usa self._voice e self._cfg (definidos em Api). Métodos com "_" não viram API da janela.
Nada de áudio passa por aqui: só o estado (desligado, aguardando, ouvindo, processando, falando).
"""

from __future__ import annotations

from jarvis.voice.ativacao import FocoEscuta, estado_base


class EscutaMixin:
    def _foco_escuta(self) -> FocoEscuta:
        if getattr(self, "_foco_esc", None) is None:
            self._foco_esc = FocoEscuta(self._cfg.voz.foco_escuta_auto)
        self._foco_esc.auto = self._cfg.voz.foco_escuta_auto
        return self._foco_esc

    def _escuta_info(self) -> dict:
        voz = getattr(self, "_voice", None)
        if voz is None:
            return {"disponivel": False, "estado": estado_base(True, ligado=False), "pausada": True}
        return {"disponivel": True, "estado": voz.estado, "pausada": voz.paused.is_set()}

    def escuta_estado(self) -> dict:
        return self._escuta_info()

    def escuta_definir(self, ligada: bool) -> dict:
        """Clique no botão do microfone: liga ou desliga a escuta (um clique, sempre)."""
        voz = getattr(self, "_voice", None)
        if voz is not None:
            voz.set_paused(not bool(ligada))
        return self._escuta_info()

    def escuta_foco(self, dentro: bool) -> dict:
        """A janela entrou (True) ou saiu (False) do modo foco. Entrar liga a escuta; sair devolve o estado anterior."""
        voz = getattr(self, "_voice", None)
        foco = self._foco_escuta()
        if voz is None:
            foco.entrar(True) if dentro else foco.sair()
            return self._escuta_info()
        if dentro:
            pausada = foco.entrar(voz.paused.is_set())
            voz.set_por_texto(True)
        else:
            pausada = foco.sair()
            voz.set_por_texto(False)
        if pausada is not None and pausada != voz.paused.is_set():
            voz.set_paused(pausada)
        return self._escuta_info()
