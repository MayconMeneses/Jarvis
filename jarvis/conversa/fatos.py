"""Fatos duráveis que o usuário conta na conversa viram PROPOSTAS de memória viva (cartão de aprovação), sem gastar IA.

Só frases do próprio usuário, em primeira pessoa, que falam de quem ele é, do que estuda/faz, das metas ou das preferências.
Nada de pergunta, dado sensível (senha, documento, valor em dinheiro, saúde) nem conversa que mexeu com e-mail, site ou arquivo.
O cartão é o mesmo da memória viva (`guardar_memoria`): só grava depois do Aprovar.
"""

from __future__ import annotations

import re

from jarvis.conversa import privacidade
from jarvis.conversa.reescrita import dobrar
from jarvis.llm import memoria_viva

MAX_POR_MENSAGEM = 1
_AREAS = (
    (re.compile(r"\b(minha meta|meus objetivos?|meu objetivo|quero (aprender|conseguir|lancar|criar|passar|chegar)|pretendo)\b"), "metas"),
    (re.compile(r"\b(meu projeto|meus projetos|estou (desenvolvendo|montando|construindo)|estou fazendo um)\b"), "projetos"),
    (re.compile(r"\b(estudo|estou (estudando|aprendendo)|faco (curso|faculdade)|tenho prova)\b"), "aprendizado"),
    (re.compile(r"\b(trabalho (com|como|na|no|em)|sou (dev|desenvolvedor|programador|estudante|analista|engenheir)\w*|minha stack)\b"), "trabalho"),
    (re.compile(r"\b(prefiro|nao gosto de|gosto de|moro em|acordo as|durmo as)\b"), "meta"),
)
_PRIMEIRA_PESSOA = re.compile(r"^(eu|meu|minha|meus|minhas|estou|sou|trabalho|estudo|moro|prefiro|quero|pretendo|gosto|nao gosto|tenho)\b")


def candidatos(texto: str) -> list[memoria_viva.Item]:
    """Até MAX_POR_MENSAGEM lembranças prováveis da mensagem do usuário (lista vazia na dúvida)."""
    frase = re.sub(r"\s+", " ", str(texto)).strip()
    baixa = dobrar(frase)
    if not (25 <= len(frase) <= 240) or "?" in frase or "[" in frase or len(frase.split()) < 5:
        return []
    if not _PRIMEIRA_PESSOA.match(baixa) or privacidade.sensivel(frase) or memoria_viva.fontes_de_terceiros(frase):
        return []
    for padrao, area in _AREAS:
        if padrao.search(baixa):
            titulo = re.sub(r"[^\w\sçãõáéíóúâêôà-]", "", frase)[:50].strip(" -")
            try:
                return [memoria_viva.validar(area, titulo, frase)]
            except ValueError:
                return []
    return []


def propor(store, mem, texto: str, origem: str = "conversa") -> int:
    """Cria os cartões de memória viva para os fatos novos; devolve quantos criou. Nunca grava."""
    criados = 0
    for item in candidatos(texto)[:MAX_POR_MENSAGEM]:
        if mem.exists(memoria_viva.ref_de(item.area, item.titulo)):
            continue  # já guardado com esse título
        memoria_viva.propor(store, mem, item, origem)
        criados += 1
    return criados
