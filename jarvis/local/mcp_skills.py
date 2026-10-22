"""Comandos de ferramentas externas (catálogo curado): listar, instalar, desativar e remover. Tudo por cartão aprovado."""

from __future__ import annotations

from jarvis.mcp_catalogo import cartoes, instalados

PADROES = [
    ("ferramentas_catalogo", r"^((que|quais) ferramentas( externas)? (eu )?(posso|pode|da pra|voce pode|tem para) instalar|(catalogo|lista) de ferramentas( externas)?|"
                             r"ferramentas (disponiveis|externas|para instalar)|que (mcps?|skills) (posso|tem para) instalar)$"),
    ("ferramentas_instaladas", r"^((que |quais )?ferramentas( externas)? (ja )?(estao )?instaladas|minhas ferramentas( externas)?|mcps? instalados?)$"),
    ("ferramentas_recusadas", r"^(ferramentas recusadas|por que (voce )?nao instala (todas|tudo|qualquer (ferramenta|mcp)))$"),
    ("ferramenta_instalar", r"^(instal\w+|adicion\w+|ativ\w+)\s+(a |o )?(ferramenta|mcp|servidor mcp)( externa| externo)?\s+(?P<alvo>.{2,60})$"),
    ("ferramenta_remover", r"^(remov\w+|desinstal\w+|desativ\w+|desligu?\w*)\s+(a |o )?(ferramenta|mcp|servidor mcp)( externa| externo)?\s+(?P<alvo>.{2,60})$"),
]
INTENTS = {p[0] for p in PADROES}


def _loja():
    from jarvis.pc import actions

    return actions.ActionStore()


def _alvo(texto: str, verbos: str) -> str:
    import re

    from jarvis.local import engine

    achado = re.search(r"(ferramenta|mcp|servidor mcp)( externa| externo)?\s+(.{2,60})$", engine.clean(texto))
    return achado[3] if achado else ""


def instalar(texto: str, cfg) -> str:
    return cartoes.propor_instalar(_alvo(texto, "instalar"), _loja())


def remover(texto: str, cfg) -> str:
    from jarvis.local import engine

    return cartoes.propor_remover(_alvo(texto, "remover"), _loja(), desativar=engine.clean(texto).startswith(("desativ", "deslig")))


MODULOS = {
    "ferramentas_catalogo": lambda t, c: cartoes.listar_texto(),
    "ferramentas_instaladas": lambda t, c: instalados.resumo(),
    "ferramentas_recusadas": lambda t, c: cartoes.recusados_texto(),
    "ferramenta_instalar": instalar,
    "ferramenta_remover": remover,
}
