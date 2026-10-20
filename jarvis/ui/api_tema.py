"""Tema da janela: hud (padrão), âmbar, esmeralda ou alto contraste. Os efeitos (completo/suave/desligado) ficam em api_visual."""

from __future__ import annotations

from jarvis import config
from jarvis.ui.api_visual import MODOS

TEMAS = ("hud", "ambar", "esmeralda", "contraste")
NOMES = {"hud": "HUD ciano", "ambar": "Âmbar", "esmeralda": "Esmeralda", "contraste": "Alto contraste"}


def tema_valido(valor: object) -> str:
    return valor if isinstance(valor, str) and valor in TEMAS else "hud"


def efeitos_validos(valor: object) -> str:
    return valor if isinstance(valor, str) and valor in MODOS else "completo"


class TemaMixin:
    def get_tema(self) -> dict:
        return {"tema": tema_valido(self._cfg.tema), "efeitos": efeitos_validos(self._cfg.efeitos_visuais), "temas": NOMES}

    def set_tema(self, tema: str) -> dict:
        """Troca o tema (lista fechada; valor desconhecido é recusado e nada muda)."""
        if not isinstance(tema, str) or tema not in TEMAS:
            return {"ok": False, "tema": tema_valido(self._cfg.tema), "mensagem": "Tema desconhecido."}
        cfg = config.load()
        cfg.tema = tema
        config.save(cfg)
        self._cfg.tema = tema
        self._diary("Tema " + NOMES[tema])
        return {"ok": True, "tema": tema, "mensagem": f"Tema {NOMES[tema]} aplicado."}
