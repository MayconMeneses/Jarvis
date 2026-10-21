"""Deduplicação: o mesmo link com enfeites e a mesma notícia em vários veículos viram um item só."""

from __future__ import annotations

import hashlib
import re
import unicodedata
import urllib.parse

from jarvis.radar.modelos import Artigo

_RASTREIO = re.compile(r"^(utm_.*|fbclid|gclid|mc_.*|ref|ref_src|igshid|cmpid|ncid|source|xtor)$", re.I)
_STOP = set("""a o as os um uma uns umas de da do das dos em na no nas nos para por pra com sem e ou que se
ao aos à às é são foi ser após apos sobre entre mais menos já não the of and to in is for on at by""".split())
LIMIAR_PARECIDO = 0.6  # Jaccard entre as palavras de dois títulos


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def normalizar_url(url: str) -> str:
    """Tira rastreio (utm_*, fbclid...), #fragmento, www., /amp e a barra final; sempre https."""
    partes = urllib.parse.urlparse(url.strip())
    host = partes.netloc.lower().removeprefix("www.")
    caminho = re.sub(r"/amp/?$", "", partes.path).rstrip("/")
    consulta = [(k, v) for k, v in urllib.parse.parse_qsl(partes.query) if not _RASTREIO.match(k)]
    return urllib.parse.urlunparse(("https", host, caminho, "", urllib.parse.urlencode(sorted(consulta)), ""))


def id_do_artigo(artigo: Artigo) -> str:
    """Identidade estável: hash do link normalizado + título normalizado."""
    bruto = normalizar_url(artigo.link) + "|" + " ".join(palavras(artigo.titulo))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()[:24]


def palavras(titulo: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]{3,}", _sem_acento(titulo)) if w not in _STOP]


def parecidos(a: str, b: str, limiar: float = LIMIAR_PARECIDO) -> bool:
    x, y = set(palavras(a)), set(palavras(b))
    return bool(x and y) and len(x & y) / len(x | y) >= limiar


def agrupar(artigos: list[Artigo]) -> list[tuple[Artigo, list[str]]]:
    """Agrupa links iguais e títulos parecidos. Devolve (representante, [outros veículos]).

    O representante é o de maior nota de fonte (empate: o mais recente). Veículos repetidos aparecem uma vez.
    """
    ordem = sorted(artigos, key=lambda a: (-a.nota_fonte, -a.quando))
    grupos: list[tuple[Artigo, list[str]]] = []
    for artigo in ordem:
        for principal, outros in grupos:
            if normalizar_url(principal.link) == normalizar_url(artigo.link) or parecidos(principal.titulo, artigo.titulo):
                if artigo.fonte != principal.fonte and artigo.fonte not in outros:
                    outros.append(artigo.fonte)
                break
        else:
            grupos.append((artigo, []))
    return grupos
