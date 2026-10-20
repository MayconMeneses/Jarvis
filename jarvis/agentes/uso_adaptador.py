"""Ponte para o agregador de uso/tokens (jarvis/uso, feito por outra frente): o painel só LÊ, não calcula nem duplica parser.

Contrato de saída: {tokens_in, tokens_out, cache, custo_usd, estimado, origem}. Se o agregador não existir ainda,
devolve None (o painel mostra "sem dado", nunca zero inventado).
"""

from __future__ import annotations

import importlib
import logging
from collections.abc import Callable

log = logging.getLogger(__name__)
CHAVES = ("tokens_in", "tokens_out", "cache", "custo_usd", "estimado", "origem")
Provedor = Callable[[], dict | None]


def normalizar(bruto) -> dict | None:
    """Só as chaves do contrato, com tipos conferidos. Qualquer outra coisa do agregador é descartada."""
    if not isinstance(bruto, dict):
        return None

    def numero(chave: str) -> int:
        v = bruto.get(chave)
        return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0 else 0

    custo = bruto.get("custo_usd")
    return {"tokens_in": numero("tokens_in"), "tokens_out": numero("tokens_out"), "cache": numero("cache"),
            "custo_usd": float(custo) if isinstance(custo, (int, float)) and not isinstance(custo, bool) else None,
            "estimado": bool(bruto.get("estimado", True)), "origem": str(bruto.get("origem") or "desconhecida")[:24]}


def provedor_padrao() -> Provedor:
    """Usa `jarvis.uso.resumo_para_agentes()` quando esse módulo existir; senão, sem dado."""
    def ler() -> dict | None:
        try:
            funcao = getattr(importlib.import_module("jarvis.uso"), "resumo_para_agentes", None)
            return funcao() if callable(funcao) else None
        except Exception:  # noqa: BLE001  (módulo ausente ou com defeito não derruba o painel)
            log.debug("agregador de uso indisponível", exc_info=True)
            return None

    return ler


def uso_atual(provedor: Provedor | None = None) -> dict | None:
    try:
        return normalizar((provedor or provedor_padrao())())
    except Exception:  # noqa: BLE001
        return None
