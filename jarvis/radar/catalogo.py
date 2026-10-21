"""Catálogo curado de fontes (semente). A IA nunca "aprova" fonte: o validador de descobrir.py é quem confere."""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.radar.dedup import _sem_acento
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Fonte

ARQUIVO = Path(__file__).with_name("dados") / "fontes_base.json"


def carregar() -> list[dict]:
    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def sugerir(nicho: str, limite: int = 12) -> list[dict]:
    """Fontes do catálogo cujo assunto aparece no nicho (ex.: "IA aplicada a saúde" → ia). Sempre inclui as gerais."""
    texto = " " + _sem_acento(nicho) + " "
    achadas = [f for f in carregar() if any(f" {n} " in texto or n in texto.split() for n in f["nichos"])]
    gerais = [f for f in carregar() if "geral" in f["nichos"] and f not in achadas]
    return (achadas + gerais)[:limite]


def semear(hist: Historico, nicho: str = "") -> int:
    """Põe no histórico as fontes do catálogo que combinam com o nicho e ainda não estão lá. Devolve quantas entraram."""
    existentes = {f.feed for f in hist.fontes()}
    novas = [f for f in sugerir(nicho) if f["feed"] not in existentes]
    for f in novas:
        hist.salvar_fonte(Fonte(f["nome"], f["feed"], f["tipo"], f["idioma"], float(f["curada"]), medida=False))
    return len(novas)
