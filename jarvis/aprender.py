"""Aprender na internet: pesquisa um tema, guarda o resumo (com as fontes) na memória e passa a consultá-lo depois.

O que vem da web é dado de terceiros e NÃO verificado: fica numa nota "Aprendizado/<tema>" que o usuário vê, edita ou apaga
na janela de memória, e a resposta sempre avisa de onde veio.
"""

from __future__ import annotations

import re

from jarvis import keys, memory_db
from jarvis.local import websearch

PREFIXO = "Aprendizado/"


def _tema(texto: str) -> str:
    return re.sub(r"^\s*(aprend\w+|estud\w+)\b\s*(sobre\b|a respeito de\b)?\s*", "", texto, flags=re.I).strip(" ?!.")[:80]


def aprender(texto: str, cfg, pesquisar=websearch.research) -> str:
    tema = _tema(texto)
    if len(tema) < 3:
        return "Sobre o que quer que eu aprenda? Exemplo: \"aprenda sobre Kubernetes\"."
    achado = pesquisar(tema, 5, brave_key=keys.get_key("brave"))
    if not achado.get("fontes"):
        return f"Não consegui aprender sobre \"{tema}\": a pesquisa não trouxe resultados (sem internet?)."
    corpo = websearch.format_answer(tema, achado)
    memory_db.open_memory(cfg).put(PREFIXO + tema, corpo + "\n\n_Aprendido da internet; não verificado. Revise antes de confiar._",
                                   "aprendizado", resumo=f"Resumo da web sobre {tema}", title=tema)
    return (f"Aprendi sobre **{tema}** e guardei na memória como \"{PREFIXO}{tema}\" (veja, edite ou apague na janela de memória). "
            "Vem da internet e não foi verificado.\n\n" + corpo)


def consultar(tema: str, cfg) -> str | None:
    """O que a Jarvis já aprendeu sobre o tema (nota de Aprendizado), ou None."""
    try:
        mem = memory_db.open_memory(cfg)
        for achado in mem.search(tema, 5):
            if achado["nota"].startswith(PREFIXO):
                return mem.read(achado["nota"], 2500)
    except Exception:
        return None
    return None
