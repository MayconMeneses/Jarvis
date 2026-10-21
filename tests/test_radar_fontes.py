import io
import time

import pytest

from jarvis.radar import catalogo, descobrir, opml, rede
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Fonte

AGORA = 1_792_500_000.0


def rss(itens):
    corpo = "".join(
        f"<item><title>{t}</title><link>https://site.com/{i}</link><pubDate>{d}</pubDate><description>{r}</description></item>"
        for i, (t, d, r) in enumerate(itens))
    return f"<?xml version='1.0'?><rss version='2.0'><channel>{corpo}</channel></rss>".encode("utf-8")


def rfc(horas):
    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(AGORA - horas * 3600))


TEXTO_LONGO = "Um resumo com bastante texto para contar como entrega de conteúdo no próprio feed da fonte."
FEED_BOM = rss([(f"IA muda a medicina {i}", rfc(i * 5), TEXTO_LONGO) for i in range(8)])


def servidor(paginas):
    """baixar() falso: {url: bytes ou Exception}."""
    def baixar(url, *a, **k):
        resposta = paginas.get(url, OSError("404"))
        if isinstance(resposta, Exception):
            raise resposta
        return resposta, "text/html" if resposta.lstrip().startswith(b"<html") else "text/xml"
    return baixar


PUBLICO = lambda host, port, *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))]


@pytest.fixture
def hist(tmp_path):
    h = Historico(tmp_path / "radar.db")
    yield h
    h.fechar()


# ── achar o feed ─────────────────────────────────────────────────────────

def test_finds_feed_by_url_alternate_link_and_common_paths():
    assert descobrir.achar_feed("https://a.com/feed", servidor({"https://a.com/feed": FEED_BOM})) == "https://a.com/feed"
    pagina = b'<html><head><link rel="alternate" type="application/atom+xml" href="/atom/todos?a=1&amp;b=2"></head></html>'
    assert descobrir.achar_feed("https://b.com/", servidor({"https://b.com/": pagina, "https://b.com/atom/todos?a=1&b=2": FEED_BOM})) \
        == "https://b.com/atom/todos?a=1&b=2"
    assert descobrir.achar_feed("https://c.com/", servidor({"https://c.com/": b"<html></html>", "https://c.com/rss.xml": FEED_BOM})) \
        == "https://c.com/rss.xml"
    assert descobrir.achar_feed("https://d.com/", servidor({"https://d.com/": b"<html></html>"})) is None


# ── validar ──────────────────────────────────────────────────────────────

def test_valid_feed_gets_measured_score_and_sample():
    r = descobrir.validar("https://a.com/feed", ["ia", "medicina"], servidor({"https://a.com/feed": FEED_BOM}), AGORA)
    assert r["ok"] and r["itens"] == 8 and r["recentes"] == 8 and r["amostra"][0].startswith("IA muda")
    assert r["partes"]["relevancia"] == 1.0 and r["medida"] == 10.0


@pytest.mark.parametrize("paginas, trecho", [
    ({}, "não baixou"),
    ({"https://a.com/feed": b"isto nao e xml"}, "não baixou"),
    ({"https://a.com/feed": rss([])}, "nenhum item"),
    ({"https://a.com/feed": rss([("Notícia velha", rfc(24 * 30), TEXTO_LONGO)])}, "feed parado"),
])
def test_dead_invalid_or_stale_feeds_are_rejected_with_reason(paginas, trecho):
    r = descobrir.validar("https://a.com/feed", [], servidor(paginas), AGORA)
    assert not r["ok"] and trecho in r["motivo"]


def test_score_is_half_measured_half_curated_and_unmeasured_is_flagged():
    assert descobrir.nota_final(10.0, 8.0) == (9.0, True)
    assert descobrir.nota_final(10.0, None) == (7.5, False)  # sem curadoria: 5 de palpite, "não medida"
    assert descobrir.nota_final(0.0, 99) == (5.0, True)  # curada limitada a 10


# ── +fonte <url> ─────────────────────────────────────────────────────────

def test_add_source_by_any_url_saves_it_with_score(hist):
    r = descobrir.adicionar("https://a.com/", hist, ["ia"], tipo="oficial",
                            baixar=servidor({"https://a.com/": b"<html></html>", "https://a.com/feed": FEED_BOM}), agora=AGORA, resolver=PUBLICO)
    assert r["ok"] and r["nome"] == "a.com" and r["feed"] == "https://a.com/feed" and r["nota"] > 5
    [fonte] = hist.fontes()
    assert fonte.tipo == "oficial" and fonte.medida is False and r["nao_medida"] is True  # credibilidade veio do tipo, não de você


def test_add_source_refuses_internal_urls_and_pages_without_feed(hist):
    interno = lambda host, port, *a, **k: [(2, 1, 6, "", ("192.168.0.10", 0))]
    r = descobrir.adicionar("http://roteador.local/feed", hist, [], resolver=interno)
    assert not r["ok"] and "rede interna" in r["motivo"] and hist.fontes() == []
    r = descobrir.adicionar("https://sem-feed.com/", hist, [], baixar=servidor({"https://sem-feed.com/": b"<html></html>"}), resolver=PUBLICO)
    assert not r["ok"] and "não encontrei" in r["motivo"]


def test_a_dead_source_never_breaks_the_others(hist):
    r = descobrir.adicionar("https://morta.com/", hist, [], baixar=servidor({"https://morta.com/feed": rss([("Velha", rfc(24 * 40), "x")])}), agora=AGORA, resolver=PUBLICO)
    assert not r["ok"] and "parado" in r["motivo"]
    ok = descobrir.adicionar("https://viva.com/", hist, [], baixar=servidor({"https://viva.com/feed": FEED_BOM}), agora=AGORA, resolver=PUBLICO)
    assert ok["ok"] and len(hist.fontes()) == 1


# ── OPML e catálogo ──────────────────────────────────────────────────────

def test_opml_round_trip_and_hostile_input():
    fontes = [Fonte('Blog "Legal" & Cia', "https://b.com/feed?a=1&b=2", "especialista", "pt", 7), Fonte("Outra", "https://o.com/rss", "oficial", "en")]
    texto = opml.exportar(fontes)
    volta = opml.importar(texto)
    assert [(f.nome, f.feed, f.tipo, f.idioma) for f in volta] == [(f.nome, f.feed, f.tipo, f.idioma) for f in fontes]
    hostil = '<opml><body><outline text="x" xmlUrl="javascript:alert(1)"/><outline text="ok" xmlUrl="https://ok.com/f"/></body></opml>'
    assert [f.nome for f in opml.importar(hostil)] == ["ok"]
    bomba = '<?xml version="1.0"?><!DOCTYPE o [<!ENTITY a "aaa"><!ENTITY b "&a;&a;">]><opml><body><outline text="&b;" xmlUrl="https://x.com/1"/></body></opml>'
    with pytest.raises(Exception):
        opml.importar(bomba)


def test_catalog_suggests_by_niche_and_seeds_once(hist):
    assert "arXiv cs.AI" in {f["nome"] for f in catalogo.sugerir("IA aplicada a saúde")}
    assert "Hacker News" in {f["nome"] for f in catalogo.sugerir("programação em Python")}
    assert "G1" in {f["nome"] for f in catalogo.sugerir("café arábica")}  # sempre as gerais
    primeira = catalogo.semear(hist, "tecnologia")
    assert primeira > 0 and catalogo.semear(hist, "tecnologia") == 0
    assert all(f.medida is False for f in hist.fontes())  # curadoria da semente, sem medição
    assert all(f["feed"].startswith("https://") for f in catalogo.carregar())
