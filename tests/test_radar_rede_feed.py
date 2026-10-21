import io
import urllib.request

import pytest

from jarvis.radar import feed_parse, rede


def resolve_para(ip):
    return lambda host, port, *a, **k: [(2, 1, 6, "", (ip, 0))]


PUBLICO = resolve_para("93.184.216.34")


class Resp(io.BytesIO):
    def __init__(self, dados, tipo="text/xml"):
        super().__init__(dados)
        self.headers = {"Content-Type": tipo}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


# ── rede: SSRF, limite, robots ───────────────────────────────────────────

@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://x.com/a", "javascript:alert(1)", "http://", "x.com/feed"])
def test_only_http_and_https_are_accepted(url):
    with pytest.raises(rede.RedeBloqueada):
        rede.validar_url(url, PUBLICO)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.20", "169.254.169.254", "172.16.0.9", "::1", "0.0.0.0"])
def test_internal_addresses_are_refused(ip):
    with pytest.raises(rede.RedeBloqueada, match="rede interna"):
        rede.validar_url("https://site-qualquer.com/feed", resolve_para(ip))


def test_unresolvable_host_is_refused_and_public_one_passes():
    def falha(host, port, *a, **k):
        raise OSError("sem DNS")
    with pytest.raises(rede.RedeBloqueada, match="resolver"):
        rede.validar_url("https://nao-existe.example/feed", falha)
    assert rede.validar_url("https://g1.globo.com/rss", PUBLICO) == "https://g1.globo.com/rss"


def test_redirect_to_internal_address_is_blocked():
    handler = rede._Redirecionamento(resolve_para("127.0.0.1"))
    req = urllib.request.Request("https://publico.com/feed")
    with pytest.raises(rede.RedeBloqueada):
        handler.redirect_request(req, None, 302, "Found", {}, "http://localhost/admin")
    assert handler.max_redirections == rede.MAX_REDIRECIONAMENTOS


def test_download_respects_the_byte_limit_and_returns_content_type():
    vistos = []

    def opener(pedido, timeout=0):
        vistos.append((pedido.full_url, pedido.get_header("User-agent"), timeout))
        return Resp(b"x" * 100, "text/xml; charset=utf-8")

    dados, tipo = rede.baixar("https://a.com/feed", limite=10, opener=opener, resolver=PUBLICO, esperar=False)
    assert dados == b"x" * 10 and "utf-8" in tipo
    assert vistos[0][1].startswith("SuperJarvis-Radar") and vistos[0][2] == rede.TIMEOUT


def test_per_host_interval_is_enforced():
    dormiu = []
    rede._ultimo.clear()
    rede._esperar("a.com", relogio=lambda: 100.0, dormir=dormiu.append)
    rede._esperar("a.com", relogio=lambda: 100.1, dormir=dormiu.append)
    rede._esperar("b.com", relogio=lambda: 100.1, dormir=dormiu.append)
    assert len(dormiu) == 1 and 0.4 < dormiu[0] < 0.6  # só o 2º pedido ao mesmo site espera


def test_robots_txt_is_honored_and_missing_robots_allows():
    rede._robots.clear()
    robots = b"User-agent: *\nDisallow: /privado/\n"
    opener = lambda pedido, timeout=0: Resp(robots, "text/plain")
    assert rede.robots_permite("https://site.com/noticia/1", opener, PUBLICO) is True
    assert rede.robots_permite("https://site.com/privado/segredo", opener, PUBLICO) is False

    def erro(pedido, timeout=0):
        raise OSError("404")
    assert rede.robots_permite("https://outro.com/qualquer", erro, PUBLICO) is True


# ── parser de feed ───────────────────────────────────────────────────────

RSS = """<?xml version="1.0"?><rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/"><channel>
<item><title>Governo aprova <b>nova</b> lei</title><link>https://exemplo.com/a?utm_source=x</link>
<pubDate>Mon, 20 Oct 2026 10:00:00 GMT</pubDate><description>&lt;p&gt;Texto &lt;script&gt;evil()&lt;/script&gt;do resumo.&lt;/p&gt;</description>
<dc:creator>Ana</dc:creator><category>Política</category></item>
<item><title>Sem link</title></item>
<item><title>Link ruim</title><link>javascript:alert(1)</link></item>
<item><title></title><link>https://exemplo.com/vazio</link></item>
</channel></rss>""".encode("utf-8")

ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Blog</title>
<entry><title>Post novo</title><link rel="alternate" href="https://blog.com/post"/><link rel="edit" href="https://blog.com/edit"/>
<updated>2026-10-20T09:30:00Z</updated><summary>Resumo atom</summary><author><name>Beto</name></author></entry>
<entry><title>Data estranha</title><link href="https://blog.com/2"/><updated>ontem de manhã</updated></entry></feed>""".encode("utf-8")


def test_rss_items_are_parsed_and_unsafe_ones_dropped():
    [a] = feed_parse.parse(RSS, "Exemplo", 8.0, "oficial")
    assert a.titulo == "Governo aprova nova lei" and a.link.startswith("https://exemplo.com/a")
    assert a.resumo == "Texto do resumo." and "evil" not in a.resumo  # script removido com o conteúdo
    assert a.autor == "Ana" and a.categorias == ("Política",) and a.nota_fonte == 8.0 and a.tipo_fonte == "oficial"
    assert a.quando == 1792490400.0


def test_atom_entries_use_alternate_link_and_iso_dates():
    novo, estranho = feed_parse.parse(ATOM, "Blog")
    assert novo.link == "https://blog.com/post" and novo.autor == "Beto" and novo.resumo == "Resumo atom"
    assert novo.quando == 1792488600.0
    assert estranho.quando == 0.0  # data inválida: 0, o filtro descarta depois


def test_xml_bomb_is_rejected():
    bomba = b'<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;">]><rss><channel><item><title>&b;</title><link>https://x.com/1</link></item></channel></rss>'
    with pytest.raises(Exception):
        feed_parse.parse(bomba, "X")


def test_dates_in_all_supported_formats():
    assert feed_parse.data_do_feed("Mon, 20 Oct 2026 10:00:00 +0000") == 1792490400.0
    assert feed_parse.data_do_feed("2026-10-20T10:00:00+00:00") == 1792490400.0
    assert feed_parse.data_do_feed("2026-10-20T07:00:00-03:00") == 1792490400.0
    assert feed_parse.data_do_feed("") == 0.0 and feed_parse.data_do_feed("lixo") == 0.0
