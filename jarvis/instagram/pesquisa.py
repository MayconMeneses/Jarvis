"""Dados públicos da web (sem login e sem raspar o Instagram): só o que as buscas oficiais já mostram, como o nº de seguidores.

Curtidas, comentários e views de posts NÃO aparecem em buscas públicas: ficam "n/d" até o usuário importar/colar.
"""

from __future__ import annotations

import re

from jarvis.instagram import fold
from jarvis.instagram.importar import normalizar_perfil, numero

_SEG = re.compile(r"(\d[\d.,]*\s*(?:mil|milh\w+|mi|k|m)?)\s*(?:seguidores|followers)\b", re.I)
AVISO = ("Curtidas, comentários e views dos posts não aparecem em pesquisas públicas (e o Instagram não permite coleta automática): "
         "para esses números, cole ou importe os dados.")


def seguidores_publicos(arroba: str, buscar=None, brave_key: str | None = None) -> dict:
    """Procura o número de seguidores em trechos de resultados públicos. Sem achar, devolve None e o motivo."""
    perfil = normalizar_perfil(arroba)
    if not perfil:
        return {"arroba": "", "seguidores": None, "fonte": None, "motivo": "informe o @ do perfil"}
    if buscar is None:
        from jarvis.local import websearch

        def buscar(consulta):
            return websearch.search(consulta, 8, brave_key=brave_key)
    try:
        resultados = buscar(f"{perfil} instagram seguidores")
    except Exception as exc:
        return {"arroba": perfil, "seguidores": None, "fonte": None, "motivo": f"a pesquisa falhou ({exc})"}
    nome = fold(perfil[1:])
    for r in resultados:
        texto = f"{r.titulo} {r.trecho}"
        achado = _SEG.search(texto)
        if achado and nome in fold(texto + " " + r.url):
            valor = numero(achado.group(1))
            if valor:
                return {"arroba": perfil, "seguidores": valor, "fonte": r.url, "motivo": ""}
    return {"arroba": perfil, "seguidores": None, "fonte": None, "motivo": f"nenhuma fonte pública trouxe os seguidores de {perfil}"}
