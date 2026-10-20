"""Gancho (como o post abre) e chamada para comentar, por regras. Sem IA: o que a regra não pega é "indefinido"."""

from __future__ import annotations

import re

from jarvis.instagram import fold

_FRASE = re.compile(r"(?<=[.!?])\s+|\n+")
_REGRAS = (
    ("numero", re.compile(r"\d")),
    ("polemica", re.compile(r"\b(mito|mitos|verdade|ninguem|erro|erros|nunca|pare de|segredo|chocante|polemic\w*|cuidado|enganad\w*|mentira|proibido)\b")),
    ("promessa", re.compile(r"\b(como|aprenda|aprender|passo a passo|guia|descubra|dicas?|truque|metodo)\b")),
    ("historia", re.compile(r"\b(quando eu|eu (fui|era|tinha|perdi|comecei|descobri|fiz|vivi|ganhei)|minha historia|um dia|certa vez)\b")),
    ("urgencia", re.compile(r"\b(hoje|agora|ultimas? (vagas|horas|dias|chances?)|so ate|ate (amanha|domingo|sexta)|acaba|corra|urgente|ultimo dia)\b")),
)
_CTA = re.compile(r"\b(comente|comenta|comentem|comentar|deixe? (aqui |nos )?(nos )?comentarios|digite|escreva (a palavra|aqui|nos comentarios)|"
                  r"me manda|manda (a palavra|aqui)|palavra[- ]chave)\b")


def primeira_frase(legenda: object) -> str:
    return next((p for p in _FRASE.split(str(legenda or "").strip()) if p.strip()), "")


def classificar_gancho(legenda: object) -> str:
    """pergunta, numero, polemica, promessa, historia, urgencia ou indefinido (nesta ordem de prioridade)."""
    frase = primeira_frase(legenda)
    if "?" in frase:
        return "pergunta"
    baixo = fold(frase)
    return next((nome for nome, regra in _REGRAS if regra.search(baixo)), "indefinido")


def tem_cta_comentario(legenda: object) -> bool:
    return bool(_CTA.search(fold(legenda)))
