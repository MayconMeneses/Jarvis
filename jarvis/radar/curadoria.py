"""Curadoria: o que entra na disputa (filtros) e quais itens vão para o boletim (5 principais + 2 de radar)."""

from __future__ import annotations

import time

from jarvis.radar.dedup import _sem_acento
from jarvis.radar.modelos import Artigo, Item
from jarvis.radar.pontuacao import _tem, eh_patrocinado


def filtrar(artigos: list[Artigo], bloqueios: list[str], janela_horas: int, agora: float | None = None) -> tuple[list[Artigo], dict[str, int]]:
    """Descarta o que está fora da janela, sem data, patrocinado ou que bate nos bloqueios. Conta os motivos."""
    agora = agora if agora is not None else time.time()
    aceitos, descartes = [], {"fora_da_janela": 0, "sem_data": 0, "patrocinado": 0, "bloqueado": 0}
    for artigo in artigos:
        if not artigo.quando:
            descartes["sem_data"] += 1  # regra do Radar: todo item leva data de publicação
        elif not (0 <= agora - artigo.quando <= janela_horas * 3600):
            descartes["fora_da_janela"] += 1
        elif eh_patrocinado(artigo):
            descartes["patrocinado"] += 1
        elif any(_tem(_sem_acento(f"{artigo.titulo} {artigo.resumo}"), b) for b in bloqueios):
            descartes["bloqueado"] += 1
        else:
            aceitos.append(artigo)
    return aceitos, descartes


def escolher(itens: list[Item], principais: int = 5, radar: int = 2, max_por_fonte: int = 2, nota_minima: int = 30) -> list[Item]:
    """Maiores notas primeiro (empate: mais recente), com teto por fonte e nota mínima. Os últimos viram "radar"."""
    ordenados = sorted((i for i in itens if i.nota >= nota_minima), key=lambda i: (i.nota, i.artigo.quando), reverse=True)
    por_fonte: dict[str, int] = {}
    escolhidos: list[Item] = []
    for item in ordenados:
        if por_fonte.get(item.artigo.fonte, 0) >= max_por_fonte:
            continue
        por_fonte[item.artigo.fonte] = por_fonte.get(item.artigo.fonte, 0) + 1
        escolhidos.append(item)
        if len(escolhidos) == principais + radar:
            break
    for posicao, item in enumerate(escolhidos):
        item.papel = "principal" if posicao < principais else "radar"
    return escolhidos
