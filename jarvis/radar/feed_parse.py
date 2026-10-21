"""RSS 2.0 e Atom → lista de Artigo. O XML vem da internet: é lido com defusedxml (sem bomba de entidades)."""

from __future__ import annotations

import html
import re
import urllib.parse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from defusedxml import ElementTree

from jarvis.radar.modelos import Artigo

_TAGS = re.compile(r"<[^>]+>")
_BLOCOS = re.compile(r"<(script|style)\b.*?</\1\s*>", re.I | re.S)


def limpar(texto: str | None, limite: int) -> str:
    """HTML → texto simples e curto. Remove script/style com o conteúdo, tags, entidades e espaços em excesso."""
    texto = _BLOCOS.sub(" ", texto or "")
    texto = html.unescape(_TAGS.sub(" ", texto))
    return re.sub(r"\s+", " ", texto).strip()[:limite]


def _nome(elemento) -> str:
    return elemento.tag.rsplit("}", 1)[-1] if isinstance(elemento.tag, str) else ""


def _texto(pai, *nomes: str) -> str:
    for filho in pai:
        if _nome(filho) in nomes:
            texto = "".join(filho.itertext()).strip()  # inclui marcação solta dentro do título (<b>...</b>)
            if texto:
                return texto
    return ""


def data_do_feed(texto: str) -> float:
    """RFC 822 (RSS), ISO 8601 (Atom, dc:date) → epoch. Sem data válida: 0."""
    texto = (texto or "").strip()
    if not texto:
        return 0.0
    try:
        momento = parsedate_to_datetime(texto)
    except (TypeError, ValueError, IndexError):
        try:
            momento = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return 0.0
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=timezone.utc)
    return momento.timestamp()


def _link(entrada) -> str:
    for filho in entrada:
        if _nome(filho) != "link":
            continue
        if filho.get("href") and filho.get("rel", "alternate") == "alternate":
            return filho.get("href").strip()
        if (filho.text or "").strip():
            return filho.text.strip()
    return ""


def _autor(entrada) -> str:
    for filho in entrada:
        if _nome(filho) == "author":
            return limpar(_texto(filho, "name") or filho.text, 80)
        if _nome(filho) == "creator":
            return limpar(filho.text, 80)
    return ""


def link_valido(link: str) -> bool:
    partes = urllib.parse.urlparse(link)
    return partes.scheme in ("http", "https") and bool(partes.netloc)


def parse(xml: bytes, fonte: str, nota_fonte: float = 5.0, tipo_fonte: str = "imprensa") -> list[Artigo]:
    raiz = ElementTree.fromstring(xml)
    artigos = []
    for entrada in raiz.iter():
        if _nome(entrada) not in ("item", "entry"):
            continue
        titulo, link = limpar(_texto(entrada, "title"), 200), _link(entrada)
        if not titulo or not link_valido(link):
            continue  # sem título ou com link que não é http(s) (javascript:, file:...): descartado
        quando = data_do_feed(_texto(entrada, "pubDate", "published", "updated", "date"))
        resumo = limpar(_texto(entrada, "description", "summary", "encoded", "content"), 300)
        categorias = tuple(limpar(c.text, 40) for c in entrada if _nome(c) == "category" and (c.text or "").strip())
        artigos.append(Artigo(fonte, titulo, link, quando, resumo, _autor(entrada), categorias[:5], nota_fonte, tipo_fonte))
    return artigos
