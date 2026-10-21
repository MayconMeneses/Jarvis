"""OPML: a lista de fontes em formato que qualquer leitor de RSS (inclusive o do celular) importa."""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

from defusedxml import ElementTree

from jarvis.radar.feed_parse import link_valido
from jarvis.radar.modelos import Fonte


def exportar(fontes: list[Fonte], titulo: str = "Radar de Notícias (Super Jarvis)") -> str:
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>', '<opml version="2.0">',
              f"  <head><title>{quoteattr(titulo)[1:-1]}</title></head>", "  <body>"]
    for f in fontes:
        linhas.append(f"    <outline type=\"rss\" text={quoteattr(f.nome)} title={quoteattr(f.nome)} "
                      f"xmlUrl={quoteattr(f.feed)} category={quoteattr(f.tipo)} language={quoteattr(f.idioma)}/>")
    return "\n".join(linhas + ["  </body>", "</opml>", ""])


def importar(texto: str | bytes) -> list[Fonte]:
    """Lê um OPML qualquer. Só entram outlines com xmlUrl http(s); nota padrão 5 (não medida)."""
    dados = texto.encode("utf-8") if isinstance(texto, str) else texto
    fontes = []
    for item in ElementTree.fromstring(dados).iter("outline"):
        feed = (item.get("xmlUrl") or "").strip()
        nome = (item.get("title") or item.get("text") or "").strip()
        if feed and nome and link_valido(feed):
            fontes.append(Fonte(nome[:80], feed, item.get("category") or "especialista", item.get("language") or "pt"))
    return fontes
