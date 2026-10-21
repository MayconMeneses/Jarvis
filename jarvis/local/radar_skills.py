"""Comandos do Radar de Notícias no motor próprio (sem IA): "radar", "ouvir radar", "radar +fonte <endereço>"...

O padrão (padroes.py) só reconhece o comando; aqui o texto ORIGINAL é lido de novo para pegar endereços e
nomes sem perder maiúsculas nem acentos. Tudo que muda configuração vem do que o próprio usuário digitou.
"""

from __future__ import annotations

import re

from jarvis.radar import servico

PADRAO = (r"^((abr\w+|ouv\w+|toc\w+|par\w+|pausa\w*|lig\w+|ativ\w+|desl\w+|rod\w+|ger\w+)\s+(o\s+|meu\s+)?)?radar(\s+.*)?$")


def _sem_acento(texto: str) -> str:
    from jarvis.local.websearch import fold

    return fold(texto)


def comando(text: str, cfg) -> str:
    original = text.strip()
    achou = re.search(r"\bradar\b", original, re.I)
    antes, depois = original[:achou.start()], original[achou.end():].strip()
    verbo_antes = _sem_acento(antes).strip().split(" ")[0] if antes.strip() else ""
    palavra, _, resto = depois.partition(" ")
    chave, resto = _sem_acento(palavra), resto.strip()

    if verbo_antes.startswith(("abr",)):
        return servico.abrir(cfg)
    if verbo_antes.startswith(("ouv", "toc")):
        return servico.ouvir(cfg)
    if verbo_antes.startswith(("par", "pausa")):
        return servico.parar()
    if verbo_antes.startswith(("lig", "ativ")):
        return servico.ligar(cfg, True)
    if verbo_antes.startswith("desl"):
        return servico.ligar(cfg, False)
    if not chave:
        return servico.rodar(cfg)  # "radar", "rodar radar", "gerar radar"
    acoes = {
        "texto": lambda: servico.rodar(cfg, so_texto=True),
        "voz": lambda: servico.ouvir(cfg), "ouvir": lambda: servico.ouvir(cfg),
        "abrir": lambda: servico.abrir(cfg), "parar": servico.parar, "pausar": servico.parar,
        "fontes": servico.fontes_texto, "+fonte": lambda: servico.adicionar(resto, cfg), "-fonte": lambda: servico.remover(resto),
        "nicho": lambda: servico.definir_nicho(resto, cfg), "semana": lambda: servico.semana(cfg),
        "arquivo": lambda: servico.arquivo(resto, cfg), "status": lambda: servico.status(cfg),
        "ligar": lambda: servico.ligar(cfg, True), "desligar": lambda: servico.ligar(cfg, False),
        "hora": lambda: servico.definir_hora(resto, cfg), "ajuda": lambda: servico.AJUDA,
    }
    if chave.startswith("busc"):
        return servico.buscar(resto, cfg)  # "radar busca <tema>": pesquisa pontual, fora da rotina
    return acoes.get(chave, lambda: servico.AJUDA)()
