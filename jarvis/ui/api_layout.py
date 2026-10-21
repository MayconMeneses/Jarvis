"""Posição das caixas arrastáveis da janela. Fica na config do Jarvis (não em localStorage: a janela do pywebview
pode abrir em modo privado e esquecer tudo). Só números de 0 a 1; sem segredo, sem texto livre."""

from __future__ import annotations

import math

from jarvis import config

# Mesma lista de js/layout-salvo.js (um teste confere).
IDS = ("telemetria", "sessoes", "uso", "tarefas", "emails", "agentes", "canal", "clima", "vagas", "noticias", "tecnologia")


def sanear(bruto: object) -> dict:
    """Aceita só {id conhecido: {x, y}} com x e y finitos em [0, 1]. JSON velho ou corrompido vira {} (layout padrão)."""
    if not isinstance(bruto, dict):
        return {}
    saida = {}
    for chave in IDS:
        p = bruto.get(chave)
        if not isinstance(p, dict):
            continue
        x, y = p.get("x"), p.get("y")
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 1 for v in (x, y)):
            saida[chave] = {"x": round(float(x), 4), "y": round(float(y), 4)}
    return saida


class LayoutMixin:
    def get_layout(self) -> dict:
        return {"ok": True, "posicoes": sanear(getattr(self._cfg, "layout_caixas", {}))}

    def set_layout(self, posicoes: dict) -> dict:
        limpo = sanear(posicoes)
        cfg = config.load()
        cfg.layout_caixas = limpo
        config.save(cfg)
        self._cfg.layout_caixas = limpo
        return {"ok": True, "posicoes": limpo}

    def restaurar_layout(self) -> dict:
        return self.set_layout({})
