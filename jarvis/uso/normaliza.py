"""Converte o "usage" de cada provedor para um formato só: {in, out, cw, cw1h, cr} (tokens).

in = entrada sem cache; out = saída; cw = escrita de cache (total); cw1h = parte da escrita de 1 h;
cr = leitura de cache. Só números: nenhum texto de conversa passa por aqui.
"""

from __future__ import annotations

CAMPOS = ("in", "out", "cw", "cw1h", "cr")


def _n(valor) -> int:
    try:
        return max(0, int(valor or 0))
    except (TypeError, ValueError):
        return 0


def vazio() -> dict:
    return dict.fromkeys(CAMPOS, 0)


def do_claude(usage: dict | None) -> dict:
    """`usage` do Claude (CLI ou linha do .jsonl)."""
    u = usage if isinstance(usage, dict) else {}
    cache = u.get("cache_creation") if isinstance(u.get("cache_creation"), dict) else {}
    cw = _n(u.get("cache_creation_input_tokens")) or (_n(cache.get("ephemeral_5m_input_tokens")) + _n(cache.get("ephemeral_1h_input_tokens")))
    return {"in": _n(u.get("input_tokens")), "out": _n(u.get("output_tokens")), "cw": cw,
            "cw1h": min(cw, _n(cache.get("ephemeral_1h_input_tokens"))), "cr": _n(u.get("cache_read_input_tokens"))}


def do_openai(usage: dict | None) -> dict:
    """`usage` de APIs compatíveis com a OpenAI (NVIDIA, Gemini no modo compatível)."""
    u = usage if isinstance(usage, dict) else {}
    detalhes = u.get("prompt_tokens_details") if isinstance(u.get("prompt_tokens_details"), dict) else {}
    cr = _n(detalhes.get("cached_tokens"))
    return {"in": max(0, _n(u.get("prompt_tokens")) - cr), "out": _n(u.get("completion_tokens")), "cw": 0, "cw1h": 0, "cr": cr}


def do_gemini(meta: dict | None) -> dict:
    """`usageMetadata` da API nativa do Gemini."""
    m = meta if isinstance(meta, dict) else {}
    cr = _n(m.get("cachedContentTokenCount"))
    return {"in": max(0, _n(m.get("promptTokenCount")) - cr), "out": _n(m.get("candidatesTokenCount")) + _n(m.get("thoughtsTokenCount")),
            "cw": 0, "cw1h": 0, "cr": cr}


def total(u: dict) -> int:
    return sum(_n(u.get(c)) for c in ("in", "out", "cw", "cr"))


def modelo_principal(model_usage) -> str:
    """Do campo `modelUsage` do resultado do Claude Code: o modelo que mais produziu."""
    if not isinstance(model_usage, dict) or not model_usage:
        return ""
    return max(model_usage, key=lambda k: _n((model_usage[k] or {}).get("outputTokens")) if isinstance(model_usage[k], dict) else 0)
