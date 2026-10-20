"""Configuração do módulo de uso (teto da cota, orçamento, alerta, câmbio), guardada no próprio banco."""

from __future__ import annotations

import json

from jarvis.uso.registro import Registro

PADRAO = {
    "plano": "",            # rótulo livre (Pro, Max 5x, Max 20x...), só informativo
    "unidade": "tokens",    # tokens (ponderados) | mensagens
    "peso_cr": 0.1,         # peso da leitura de cache nos tokens ponderados
    "teto_5h": None,        # teto da janela de 5 h na unidade escolhida (calibrável)
    "teto_semana": None,    # teto semanal
    "semana_dow": 0,        # dia do reset semanal: 0 = segunda ... 6 = domingo
    "semana_hora": 0,       # hora do reset semanal
    "orcamento_mensal": None,  # USD por mês
    "alerta_pct": 80,       # limiar de aviso (cota e orçamento)
    "cotacao_brl": None,    # R$ por US$, digitada (nenhuma chamada externa)
}


def _numero(valor, minimo=0.0):
    if valor is None or str(valor).strip() == "":
        return None
    try:
        numero = float(str(valor).replace(",", "."))
    except ValueError:
        return None
    return numero if numero >= minimo else None


def carregar(reg: Registro) -> dict:
    try:
        guardado = json.loads(reg.meta("config", "{}"))
    except json.JSONDecodeError:
        guardado = {}
    return {**PADRAO, **{k: v for k, v in guardado.items() if k in PADRAO}}


def salvar(reg: Registro, novo: dict) -> dict:
    """Valida cada campo (valor inválido mantém o anterior) e grava."""
    atual = carregar(reg)
    for campo in ("teto_5h", "teto_semana", "orcamento_mensal", "cotacao_brl"):
        if campo in novo:
            atual[campo] = _numero(novo[campo])
    if "peso_cr" in novo and _numero(novo["peso_cr"]) is not None:
        atual["peso_cr"] = min(1.0, _numero(novo["peso_cr"]))
    if "alerta_pct" in novo and _numero(novo["alerta_pct"]) is not None:
        atual["alerta_pct"] = min(100, max(1, int(_numero(novo["alerta_pct"]))))
    if novo.get("unidade") in ("tokens", "mensagens"):
        atual["unidade"] = novo["unidade"]
    if "semana_dow" in novo and _numero(novo["semana_dow"]) is not None:
        atual["semana_dow"] = int(_numero(novo["semana_dow"])) % 7
    if "semana_hora" in novo and _numero(novo["semana_hora"]) is not None:
        atual["semana_hora"] = int(_numero(novo["semana_hora"])) % 24
    if "plano" in novo:
        atual["plano"] = str(novo["plano"])[:40]
    reg.definir_meta("config", json.dumps(atual))
    return atual
