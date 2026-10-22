"""Ferramentas de web do cinto: pesquisar (Brave com a chave do usuário, senão Wikipédia/DuckDuckGo) e ler uma página.

A busca só fala com endereços fixos de buscadores. Ler página usa o leitor protegido contra SSRF
(jarvis/info/leitor_texto.py): só http(s) público, cada redirecionamento rechecado, tamanho e tempo limitados.
Tudo que volta é conteúdo de terceiros (a marca <dados_externos> e o filtro de ordens são aplicados em ferramentas_base).
"""

from __future__ import annotations

from jarvis.info import leitor_texto
from jarvis.llm.ferramentas_base import Ferramenta
from jarvis.local import websearch

MAX_RESULTADOS = 8
TRECHO = 220


def pesquisar_web(consulta: str, limite: int = 5, buscar=None, chave=None) -> str:
    if chave is None:
        from jarvis import keys

        chave = keys.get_key("brave")
    try:
        achados = (buscar or websearch.search)(consulta, limite=max(1, min(limite, MAX_RESULTADOS)), brave_key=chave)
    except Exception as exc:  # noqa: BLE001 - rede/serviço fora do ar vira aviso curto
        raise RuntimeError("a pesquisa na internet não respondeu agora") from exc
    if not achados:
        return f'Nada encontrado para "{consulta[:80]}".'
    fonte = "Brave" if chave else "Wikipédia e DuckDuckGo (sem chave)"
    linhas = [f"Resultados ({fonte}):"]
    for n, r in enumerate(achados, 1):
        linhas.append(f"{n}. {r.titulo[:120]} — {r.url[:200]}" + (f"\n   {r.trecho[:TRECHO]}" if r.trecho else ""))
    return "\n".join(linhas)


def ler_pagina(url: str, baixar=None) -> str:
    try:
        return f"Texto da página {url[:200]}:\n" + (baixar or leitor_texto.baixar_artigo)(url)
    except leitor_texto.LeituraErro as exc:
        raise RuntimeError(str(exc)) from None


FERRAMENTAS = (
    Ferramenta("pesquisar_web", "Pesquisa na internet e devolve títulos, endereços e trechos. Use para fatos atuais ou que você não sabe.",
               {"consulta": {"type": "string", "description": "o que pesquisar", "maxLength": 200},
                "limite": {"type": "integer", "description": "quantos resultados (1 a 8)", "minimum": 1, "maximum": MAX_RESULTADOS}},
               ("consulta",), pesquisar_web, externo=True),
    Ferramenta("ler_pagina", "Lê o texto principal de uma página pública (http/https) que apareceu numa pesquisa ou que o usuário citou.",
               {"url": {"type": "string", "description": "endereço completo da página", "maxLength": 2000}},
               ("url",), ler_pagina, externo=True),
)
