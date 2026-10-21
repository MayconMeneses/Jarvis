"""Descoberta e validação de fontes: dada uma URL, acha o feed, confere se está vivo e dá uma nota de 0 a 10.

Nota = metade medida (frequência, completude, entrega de texto, relevância) + metade curada (credibilidade e
originalidade NÃO são mensuráveis por programa: vêm do catálogo ou de você; sem isso, vale 5 e fica "não medido").
"""

from __future__ import annotations

import re
import socket
import time
import urllib.parse

from jarvis.radar import feed_parse, rede
from jarvis.radar.dedup import _sem_acento
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Fonte

CAMINHOS = ("/feed", "/rss", "/rss.xml", "/feed.xml", "/atom.xml", "/index.xml", "/feeds/posts/default", "/blog/rss")
_LINK_ALTERNATE = re.compile(r"<link\b[^>]*>", re.I)
CREDIBILIDADE_PADRAO = {"oficial": 8.0, "cientifico": 8.0, "imprensa": 6.0, "especialista": 6.0, "comunidade": 5.0, "contraponto": 5.0}


def _eh_feed(dados: bytes) -> bool:
    try:
        return bool(feed_parse.parse(dados, "teste"))
    except Exception:
        return False


def _feeds_da_pagina(html: str, base: str) -> list[str]:
    achados = []
    for tag in _LINK_ALTERNATE.findall(html):
        if re.search(r"rel=[\"']?alternate", tag, re.I) and re.search(r"type=[\"']?application/(rss|atom)\+xml", tag, re.I):
            href = re.search(r"href=[\"']([^\"']+)[\"']", tag, re.I)
            if href:
                achados.append(urllib.parse.urljoin(base, href.group(1).replace("&amp;", "&")))
    return achados


def achar_feed(url: str, baixar=rede.baixar) -> str | None:
    """A própria URL, ou o `<link rel=alternate>` da página, ou os caminhos comuns. None se nada servir."""
    candidatos: list[str] = []
    try:
        dados, tipo = baixar(url)
        if _eh_feed(dados):
            return url
        candidatos += _feeds_da_pagina(rede.decodificar(dados, tipo), url)
    except Exception:
        pass
    raiz = urllib.parse.urlparse(url)
    candidatos += [f"{raiz.scheme}://{raiz.netloc}{c}" for c in CAMINHOS]
    for candidato in dict.fromkeys(candidatos):  # sem repetir, na ordem
        try:
            if _eh_feed(baixar(candidato)[0]):
                return candidato
        except Exception:
            continue
    return None


def validar(feed: str, palavras_chave: list[str], baixar=rede.baixar, agora: float | None = None) -> dict:
    """Entra só se: baixa, é XML válido, tem item nos últimos 7 dias e os itens têm título, link e data."""
    agora = agora if agora is not None else time.time()
    try:
        dados, _ = baixar(feed)
        artigos = feed_parse.parse(dados, "validacao")
    except Exception as exc:
        return {"ok": False, "motivo": f"não baixou ou não é um feed válido ({type(exc).__name__})"}
    if not artigos:
        return {"ok": False, "motivo": "o feed não tem nenhum item com título e link"}
    recentes = [a for a in artigos if a.quando and 0 <= agora - a.quando <= 7 * 86400]
    if not recentes:
        return {"ok": False, "motivo": "feed parado: nenhum item nos últimos 7 dias"}
    com_data = sum(1 for a in artigos if a.quando) / len(artigos)
    com_texto = sum(1 for a in artigos if len(a.resumo) >= 60) / len(artigos)
    titulos = [_sem_acento(a.titulo) for a in artigos]
    relevancia = (sum(1 for t in titulos if any(_sem_acento(p) in t for p in palavras_chave)) / len(titulos)) if palavras_chave else None
    partes = {"frequencia": min(1.0, len(recentes) / 7), "completude": com_data, "entrega": com_texto}
    if relevancia is not None:
        partes["relevancia"] = min(1.0, relevancia * 3)  # 1 em cada 3 títulos já é um ótimo aproveitamento
    medida = 10 * sum(partes.values()) / len(partes)
    return {"ok": True, "itens": len(artigos), "recentes": len(recentes), "medida": round(medida, 1),
            "partes": {k: round(v, 2) for k, v in partes.items()}, "amostra": [a.titulo for a in artigos[:3]]}


def nota_final(medida: float, curada: float | None) -> tuple[float, bool]:
    """Devolve (nota 0–10, foi_curada). Sem nota curada vale 5 e a fonte fica marcada como "não medida"."""
    base = 5.0 if curada is None else max(0.0, min(10.0, curada))
    return round((medida + base) / 2, 1), curada is not None


def adicionar(url: str, hist: Historico, palavras_chave: list[str], nome: str = "", tipo: str = "especialista",
              curada: float | None = None, baixar=rede.baixar, agora: float | None = None, resolver=None) -> dict:
    """`radar +fonte <url>`: acha o feed, valida, dá a nota e guarda. Nada de mexer em código."""
    try:
        rede.validar_url(url, resolver or socket.getaddrinfo)
    except rede.RedeBloqueada as exc:
        return {"ok": False, "motivo": str(exc)}
    feed = achar_feed(url, baixar)
    if feed is None:
        return {"ok": False, "motivo": "não encontrei um feed RSS/Atom nesse endereço"}
    relatorio = validar(feed, palavras_chave, baixar, agora)
    if not relatorio["ok"]:
        return {**relatorio, "feed": feed}
    nota, curada_ok = nota_final(relatorio["medida"], curada if curada is not None else CREDIBILIDADE_PADRAO.get(tipo))
    nome = nome or urllib.parse.urlparse(feed).netloc.removeprefix("www.")
    hist.salvar_fonte(Fonte(nome, feed, tipo, "pt", nota, medida=curada is not None))
    return {**relatorio, "feed": feed, "nome": nome, "nota": nota, "nao_medida": curada is None}
