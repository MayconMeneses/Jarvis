"""Manchetes por RSS. O XML vem da internet: é lido com defusedxml."""

from __future__ import annotations

import html
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

FEEDS = {
    "gerais": {
        "G1": "https://g1.globo.com/rss/g1/",
        "BBC Brasil": "https://feeds.bbci.co.uk/portuguese/rss.xml",
        "Agência Brasil": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
    },
    "tecnologia": {
        "Tecnoblog": "https://tecnoblog.net/feed/",
        "Canaltech": "https://canaltech.com.br/rss/",
        "Olhar Digital": "https://olhardigital.com.br/feed/",
    },
}
_TAGS = re.compile(r"<[^>]+>")


def _clean(text: str | None, limit: int) -> str:
    text = html.unescape(_TAGS.sub(" ", text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def parse(xml_bytes: bytes, source: str) -> list[dict]:
    root = ElementTree.fromstring(xml_bytes)
    items = []
    for item in root.iter("item"):
        title = _clean(item.findtext("title"), 200)
        if not title:
            continue
        when = None
        try:
            when = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            pass
        items.append({
            "fonte": source,
            "titulo": title,
            "resumo": _clean(item.findtext("description"), 280),
            "link": (item.findtext("link") or "").strip(),
            "_quando": when.timestamp() if when else 0,
        })
    return items


def fetch(url: str, opener=urllib.request.urlopen) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "SuperJarvis/0.1 (assistente pessoal)"})
    with opener(request, timeout=15) as resp:
        return resp.read(3_000_000)


def headlines(kind: str = "gerais", limit: int = 5, feeds: dict | None = None, opener=urllib.request.urlopen) -> dict:
    """Manchetes mais recentes, alternando as fontes para não repetir um só portal."""
    feeds = feeds or FEEDS.get(kind, {})
    per_source: dict[str, list[dict]] = {}
    errors = []

    def load(item):
        name, url = item
        try:
            return name, parse(fetch(url, opener), name)
        except Exception as exc:  # um portal fora do ar não derruba os outros
            return name, exc

    with ThreadPoolExecutor(max_workers=len(feeds) or 1) as pool:
        for name, result in pool.map(load, feeds.items()):
            if isinstance(result, Exception):
                errors.append(f"{name}: {result}")
            else:
                per_source[name] = sorted(result, key=lambda i: i["_quando"], reverse=True)

    chosen: list[dict] = []
    seen = set()
    while len(chosen) < limit and any(per_source.values()):
        for name in list(per_source):
            if per_source[name] and len(chosen) < limit:
                item = per_source[name].pop(0)
                key = item["titulo"].lower()[:60]
                if key not in seen:
                    seen.add(key)
                    chosen.append({k: v for k, v in item.items() if k != "_quando"})
    return {"manchetes": chosen, "avisos": errors}


# ── notícias por assunto (Google News RSS), com cache em disco ──────────
GOOGLE_NEWS = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
TTL_ASSUNTO = 45 * 60
_cache_mem: dict[str, tuple[float, dict]] = {}


def _separar_fonte(titulo: str) -> tuple[str, str]:
    """O Google News entrega "Título - Fonte"."""
    corpo, sep, fonte = titulo.rpartition(" - ")
    return (corpo, fonte) if sep and corpo and len(fonte) <= 40 else (titulo, "Google News")


def por_assunto(assunto: str, limite: int = 5, opener=urllib.request.urlopen, agora=None) -> dict:
    """Manchetes de um assunto livre ("IA", "dólar"). Cache de 45 min por assunto. Títulos são dado de terceiros."""
    import time
    import urllib.parse

    assunto = re.sub(r"\s+", " ", assunto).strip()[:80]
    if not assunto:
        return {"manchetes": [], "avisos": ["diga o assunto"]}
    agora = time.time() if agora is None else agora
    chave = assunto.lower()
    if chave in _cache_mem and agora - _cache_mem[chave][0] < TTL_ASSUNTO:
        achado = _cache_mem[chave][1]
    else:
        try:
            itens = sorted(parse(fetch(GOOGLE_NEWS.format(q=urllib.parse.quote(assunto)), opener), "Google News"),
                           key=lambda i: i["_quando"], reverse=True)
        except Exception as exc:
            return {"manchetes": [], "avisos": [f"não consegui buscar notícias agora ({type(exc).__name__})"]}
        vistos, lista = set(), []
        for item in itens:
            titulo, fonte = _separar_fonte(item["titulo"])
            if titulo.lower()[:60] in vistos:
                continue
            vistos.add(titulo.lower()[:60])
            lista.append({"fonte": fonte, "titulo": titulo, "resumo": "", "link": item["link"]})
        achado = {"manchetes": lista, "avisos": []}
        _cache_mem[chave] = (agora, achado)
    return {"manchetes": achado["manchetes"][:limite], "avisos": achado["avisos"]}
