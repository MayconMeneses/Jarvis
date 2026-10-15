"""Pesquisa na internet SEM IA generativa.

Fontes oficiais que permitem uso automático (nada de raspar buscadores nem contornar
verificação anti-robô):
- Brave Search API (web completa; chave gratuita, ~2.000 buscas/mês), se cadastrada;
- Wikipedia em português e inglês (sem chave), com checagem de relevância;
- DuckDuckGo Instant Answer API oficial (sem chave), como complemento.
Depois abre as páginas, extrai o texto principal e monta um resumo EXTRATIVO: só frases
que estão nos sites, escolhidas por pontuação de palavras da pergunta. Nada é inventado.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from html.parser import HTMLParser

# Identificação honesta (a política da Wikimedia pede um User-Agent descritivo).
UA = "SuperJarvis/0.12 (assistente pessoal de uso individual; baixo volume) Python-urllib"
CACHE_SECONDS = 24 * 3600
MIN_INTERVAL = 0.6  # segundos entre pedidos ao mesmo site
_cache: dict[str, tuple[float, str, str]] = {}
_last_hit: dict[str, float] = {}
_lock = __import__("threading").Lock()
STOPWORDS = set("""a o as os um uma uns umas de da do das dos em na no nas nos para por pra pro com sem
e ou que qual quais quem como quando onde porque porquê se ser é são era foi sobre entre
me te se lhe nos vos eu tu ele ela eles elas isso isto aquilo esse essa este esta mais menos
muito pouco já não sim ao à às aos seu sua seus suas meu minha the of and to in is what how
serve servem servir funciona funcionam funcionar significa significado explique explica explicar
defina definicao definição exemplo exemplos pesquise pesquisa pesquisar procure busque buscar
fale diga mostre quero saber pode poderia jarvis hoje agora atual atualmente melhor""".split())


@dataclass
class Result:
    titulo: str
    url: str
    trecho: str = ""


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def keywords(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9+#.]{2,}", fold(text)) if w not in STOPWORDS]


def _get(url: str, opener=urllib.request.urlopen, limit: int = 1_500_000, timeout: int = 12) -> tuple[str, str]:
    """GET com cache de 1 dia e intervalo mínimo por site (respeita quem nos atende)."""
    import time

    now = time.time()
    cached = _cache.get(url)
    if cached and now - cached[0] < CACHE_SECONDS:
        return cached[1], cached[2]
    host = urllib.parse.urlparse(url).netloc
    with _lock:
        wait = MIN_INTERVAL - (now - _last_hit.get(host, 0))
        _last_hit[host] = now + max(0.0, wait)
    if wait > 0:
        time.sleep(wait)
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with opener(request, timeout=timeout) as resp:
        kind = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else "text/html"
        raw = resp.read(limit)
    charset = re.search(r"charset=([\w-]+)", kind)
    text = raw.decode(charset.group(1) if charset else "utf-8", errors="replace")
    _cache[url] = (time.time(), text, kind)
    return text, kind


# ── busca ────────────────────────────────────────────────────────────────

def _strip_tags(text: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", text or "")).split())


def brave(query: str, key: str, limit: int = 10, opener=urllib.request.urlopen) -> list[Result]:
    """Web completa pela Brave Search API (oficial; chave gratuita)."""
    url = "https://api.search.brave.com/res/v1/web/search?" + urllib.parse.urlencode(
        {"q": query, "count": min(limit, 20), "country": "BR", "search_lang": "pt-br"})
    request = urllib.request.Request(url, headers={"Accept": "application/json", "X-Subscription-Token": key, "User-Agent": UA})
    with opener(request, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return [Result(_strip_tags(r.get("title")), r.get("url", ""), _strip_tags(r.get("description")))
            for r in data.get("web", {}).get("results", []) if r.get("url", "").startswith("http")]


def relevant(title: str, excerpt: str, terms: list[str]) -> bool:
    """O resultado tem relação com a pergunta? (evita "Gandhi" para uma pergunta sobre Docker)"""
    if not terms:
        return False
    words = set(keywords(title + " " + excerpt))
    in_title = set(keywords(title)) & set(terms)
    hits = sum(1 for t in terms if t in words)
    if len(terms) <= 2:
        return bool(in_title)  # pergunta curta: o tema tem de estar no título
    return bool(in_title) and hits >= (2 * len(terms) + 2) // 3


def wikipedia(query: str, lang: str = "pt", limit: int = 3, opener=urllib.request.urlopen) -> list[Result]:
    terms = keywords(query)
    if not terms:
        return []
    base = f"https://{lang}.wikipedia.org"
    url = f"{base}/w/rest.php/v1/search/page?" + urllib.parse.urlencode({"q": " ".join(terms), "limit": limit})
    pages = json.loads(_get(url, opener)[0]).get("pages", [])
    found = []
    for page in pages:
        excerpt = _strip_tags(page.get("excerpt"))
        if not relevant(page.get("title", ""), excerpt, terms):
            continue
        key = page["key"]
        link = f"{base}/wiki/{urllib.parse.quote(key)}"
        text = excerpt
        if len(found) < 2:  # resumo completo só das 2 melhores (menos pedidos)
            try:
                text = json.loads(_get(f"{base}/api/rest_v1/page/summary/" + urllib.parse.quote(key), opener)[0]).get("extract") or excerpt
            except Exception:
                pass
        found.append(Result(page.get("title", key), link, text))
    return found


def ddg_instant(query: str, opener=urllib.request.urlopen) -> list[Result]:
    """API oficial Instant Answer do DuckDuckGo (resumos e tópicos relacionados)."""
    url = "https://api.duckduckgo.com/?" + urllib.parse.urlencode(
        {"q": " ".join(keywords(query)) or query, "format": "json", "no_html": 1, "skip_disambig": 1})
    data = json.loads(_get(url, opener)[0])
    found = []
    if data.get("AbstractText") and data.get("AbstractURL"):
        found.append(Result(data.get("Heading", ""), data["AbstractURL"], data["AbstractText"]))
    for topic in data.get("RelatedTopics", [])[:5]:
        if topic.get("FirstURL") and topic.get("Text"):
            found.append(Result(topic["Text"][:80], topic["FirstURL"], topic["Text"]))
    return found


def search(query: str, limit: int = 8, brave_key: str | None = None, opener=urllib.request.urlopen) -> list[Result]:
    """Junta as fontes disponíveis, sem repetir URL. Uma fonte fora do ar não derruba as outras."""
    collected: list[Result] = []

    def safe(load) -> list[Result]:
        try:
            return load()
        except Exception:
            return []

    if brave_key:
        collected += safe(lambda: brave(query, brave_key, limit, opener))
    portuguese = safe(lambda: wikipedia(query, "pt", 3, opener))
    collected += portuguese
    if len(portuguese) < 2:  # inglês só quando o português não basta (evita homônimos)
        collected += safe(lambda: wikipedia(query, "en", 2, opener))
    collected += safe(lambda: ddg_instant(query, opener))
    seen, results = set(), []
    for r in collected:
        if r.url not in seen:
            seen.add(r.url)
            results.append(r)
    return results[:limit]


# ── leitura de páginas ───────────────────────────────────────────────────

class _TextParser(HTMLParser):
    SKIP = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button"}
    KEEP = {"p", "li", "h1", "h2", "h3", "td", "blockquote"}

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._skip = 0
        self._buffer: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.KEEP and not self._skip:
            self._buffer = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.KEEP and self._buffer is not None:
            text = " ".join("".join(self._buffer).split())
            if len(text) > 30:
                self.blocks.append(text)
            self._buffer = None

    def handle_data(self, data):
        if self._buffer is not None and not self._skip:
            self._buffer.append(data)


def page_text(url: str, opener=urllib.request.urlopen) -> str:
    content, kind = _get(url, opener)
    if "html" not in kind and "text" not in kind:
        return ""
    parser = _TextParser()
    parser.feed(content)
    return "\n".join(parser.blocks)


# ── resumo extrativo ─────────────────────────────────────────────────────

def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9\"“])", text.replace("\n", " "))
    return [p.strip() for p in parts if 40 <= len(p.strip()) <= 320]


def extract(query: str, docs: list[tuple[int, str]], top: int = 6) -> list[tuple[str, int]]:
    """Frases mais relevantes: palavras da pergunta, termos que aparecem em várias fontes."""
    terms = set(keywords(query))
    if not terms:
        return []
    # (frase, fonte, palavras, posição da frase dentro do próprio texto)
    candidates = [(s, n, set(keywords(s)), i) for n, text in docs for i, s in enumerate(sentences(text))]
    spread = {t: len({n for _, n, words, _ in candidates if t in words}) for t in terms}
    # Centralidade (ideia do TextRank): o quanto a frase compartilha conteúdo com as outras
    # frases do mesmo texto. Frases centrais representam melhor o assunto do documento.
    by_doc: dict[int, list[set]] = {}
    for _, source, words, _ in candidates:
        by_doc.setdefault(source, []).append(words)

    def centrality(source: int, words: set) -> float:
        others = [w for w in by_doc[source] if w is not words and w]
        if not others or not words:
            return 0.0
        return sum(len(words & w) / len(words | w) for w in others) / len(others)

    scored = []
    for sentence, source, words, position in candidates:
        hits = terms & words
        if not hits and position > 2:
            continue  # sem termo da pergunta, só entra se estiver no começo do texto
        score = sum(1 + 0.5 * spread[t] for t in hits) + 8 * centrality(source, words)
        score *= 1 + 1.2 / (1 + position)  # o começo do texto costuma resumir o assunto
        if re.search(r"\b(e|sao|foi|significa|consiste|refere)\b", fold(sentence)[:120]):
            score *= 1.25  # frase de definição ("X é ...")
        scored.append((score, sentence, source, words))
    chosen: list[tuple[str, int]] = []
    kept: list[set] = []
    for score, sentence, source, words in sorted(scored, key=lambda x: -x[0]):
        if any(len(words & w) / max(1, len(words | w)) > 0.55 for w in kept):
            continue  # quase igual a uma já escolhida
        chosen.append((sentence, source))
        kept.append(words)
        if len(chosen) == top:
            break
    return chosen


def research(query: str, sites: int = 5, brave_key: str | None = None, opener=urllib.request.urlopen) -> dict:
    """Pesquisa completa sem IA: fontes, trechos e resumo extrativo."""
    sources = search(query, limit=max(sites, 3), brave_key=brave_key, opener=opener)

    def read(item: tuple[int, Result]) -> tuple[int, str]:
        n, result = item
        if ("wikipedia.org" in result.url or "duckduckgo.com" in result.url) and result.trecho:
            return n, result.trecho  # já é o resumo oficial
        try:
            return n, page_text(result.url, opener)
        except Exception:
            return n, result.trecho  # site fora do ar: usa ao menos o trecho da busca
    with ThreadPoolExecutor(max_workers=4) as pool:
        docs = list(pool.map(read, enumerate(sources, 1)))
    return {"fontes": sources, "resumo": extract(query, docs), "lidos": sum(1 for _, t in docs if t)}


def format_answer(query: str, found: dict) -> str:
    if not found["fontes"]:
        return f"Não encontrei resultados na internet para \"{query}\"."
    lines = [f"**Resumo extraído de {found['lidos']} sites** (modo independente: frases dos próprios sites, sem IA):"]
    if found["resumo"]:
        lines += [f"- {sentence} [{n}]" for sentence, n in found["resumo"]]
    else:
        lines += [f"- {r.trecho} [{n}]" for n, r in enumerate(found["fontes"], 1) if r.trecho][:4]
    lines.append("\n**Fontes:**")
    lines += [f"{n}. {r.titulo or r.url} — {r.url}" for n, r in enumerate(found["fontes"], 1)]
    return "\n".join(lines)
