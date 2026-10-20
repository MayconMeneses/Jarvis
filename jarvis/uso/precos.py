"""Tabela de preços EDITÁVEL (USD por 1 milhão de tokens) em precos_ia.json, na pasta de dados.

Os valores de fábrica são ESTIMATIVAS A CONFERIR com a página oficial de preços de cada provedor.
Modelo sem preço nunca vira "custo zero": aparece como "sem preço" até o dono preencher.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from jarvis.config import data_dir

# Escrita de cache de 5 min custa 1,25x a entrada; de 1 h, 2x; leitura de cache, 0,1x (a conferir).
MULTIPLICADORES = {"cw5": 1.25, "cw1h": 2.0, "cr": 0.1}
FABRICA = {
    "a_conferir": True,
    "multiplicadores": MULTIPLICADORES,
    "modelos": {
        "claude-fable-5-1": {"in": None, "out": None},
        "claude-opus-5-5": {"in": 15.0, "out": 75.0},
        "claude-sonnet-5-5": {"in": 3.0, "out": 15.0},
        "claude-haiku-5-5": {"in": 1.0, "out": 5.0},
    },
}
_DATA = re.compile(r"-\d{8}$")
_COLCHETE = re.compile(r"\[.*\]$")


def arquivo() -> Path:
    return data_dir() / "precos_ia.json"


def carregar(caminho: Path | None = None) -> dict:
    caminho = caminho or arquivo()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(FABRICA))
    dados.setdefault("multiplicadores", dict(MULTIPLICADORES))
    dados.setdefault("modelos", {})
    return dados


def salvar(dados: dict, caminho: Path | None = None) -> dict:
    """Valida e grava. Preço vazio vira "sem preço" (None); negativo ou texto é rejeitado."""
    caminho = caminho or arquivo()
    limpo = {"a_conferir": bool(dados.get("a_conferir", True)), "multiplicadores": dict(MULTIPLICADORES), "modelos": {}}
    for chave, valor in (dados.get("multiplicadores") or {}).items():
        if chave in MULTIPLICADORES:
            limpo["multiplicadores"][chave] = _numero(valor, MULTIPLICADORES[chave])
    for modelo, p in (dados.get("modelos") or {}).items():
        nome = normalizar(modelo)
        if nome and isinstance(p, dict):
            limpo["modelos"][nome] = {"in": _numero(p.get("in"), None), "out": _numero(p.get("out"), None)}
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(limpo, ensure_ascii=False, indent=2), encoding="utf-8")
    return limpo


def _numero(valor, padrao):
    if valor is None or str(valor).strip() == "":
        return padrao
    try:
        numero = float(str(valor).replace(",", "."))
    except ValueError:
        return padrao
    return numero if numero >= 0 else padrao


def normalizar(modelo: str) -> str:
    """Tira sufixo de data e colchetes ("claude-opus-5-5-20261001", "...[1m]"); o resto fica exato."""
    return _DATA.sub("", _COLCHETE.sub("", str(modelo or "").strip().lower()))


def preco_de(modelo: str, tabela: dict) -> dict | None:
    """{"in", "out"} se o modelo tem preço preenchido; None se não existe ou está vazio."""
    p = (tabela.get("modelos") or {}).get(normalizar(modelo))
    if not p or p.get("in") is None or p.get("out") is None:
        return None
    return p


def calcular(modelo: str, uso: dict, tabela: dict | None = None) -> tuple[float, bool]:
    """(custo em USD, preço_conhecido). Sem preço devolve (0.0, False): quem mostra deve destacar."""
    tabela = tabela or carregar()
    p = preco_de(modelo, tabela)
    if p is None:
        return 0.0, False
    m = tabela["multiplicadores"]
    cw, cw1h = int(uso.get("cw", 0)), min(int(uso.get("cw", 0)), int(uso.get("cw1h", 0)))
    entrada = (int(uso.get("in", 0)) + (cw - cw1h) * m.get("cw5", 1.25) + cw1h * m.get("cw1h", 2.0) + int(uso.get("cr", 0)) * m.get("cr", 0.1)) * p["in"]
    return (entrada + int(uso.get("out", 0)) * p["out"]) / 1_000_000, True
