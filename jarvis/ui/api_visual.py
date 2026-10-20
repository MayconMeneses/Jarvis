"""Efeitos visuais do orbe: chave manual completo/suave/desligado, salva na configuração."""

from __future__ import annotations

from jarvis import config

MODOS = ("completo", "suave", "desligado")


class VisualMixin:
    def efeitos_visuais(self) -> str:
        modo = self._cfg.efeitos_visuais
        return modo if modo in MODOS else "completo"

    def definir_efeitos_visuais(self, modo: str) -> str:
        """Guarda o modo escolhido (valor inválido vira "completo") e devolve o que ficou valendo."""
        self._cfg.efeitos_visuais = modo if modo in MODOS else "completo"
        config.save(self._cfg)
        return self._cfg.efeitos_visuais
