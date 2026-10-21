"""Caixas arrastáveis (layout salvo, limites, zona do orbe) e caixa "Notícias de tecnologia"."""

import json
import re
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from jarvis import config
from jarvis.ui import api_info, api_layout, web
from jarvis.ui.api_info import InfoMixin
from jarvis.ui.api_layout import LayoutMixin

JS, CSS = web.BASE / "js", web.BASE / "css"
precisa_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")


def _m(expressao: str):
    caminho = json.dumps((JS / "layout-salvo.js").as_posix())
    saida = subprocess.run(["node", "-e", f"const M = require({caminho}); console.log(JSON.stringify({expressao}));"],
                           capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout
    return json.loads(saida)


AREA = "{w:1000,h:600}"
ZONA = "{x:400,y:100,w:200,h:300}"


@precisa_node
def test_limites_mantem_a_caixa_dentro_da_janela():
    assert _m(f"M.limitar({{x:-50,y:900,w:200,h:100}}, {AREA})") == {"x": 0, "y": 500, "w": 200, "h": 100}
    assert _m(f"M.limitar({{x:950,y:0,w:200,h:100}}, {AREA})")["x"] == 800
    assert _m("M.limitar({x:5,y:5,w:2000,h:900}, {w:1000,h:600})")["x"] == 0  # maior que a janela: encosta no canto


@precisa_node
def test_zona_do_orbe_empurra_pelo_menor_caminho_ou_rejeita():
    livre = _m(f"M.resolver({{x:50,y:50,w:100,h:100}}, {AREA}, {ZONA})")
    assert livre == {"x": 50, "y": 50, "empurrada": False, "rejeitada": False}
    r = _m(f"M.resolver({{x:380,y:200,w:100,h:100}}, {AREA}, {ZONA})")  # invade pela borda esquerda
    assert r["empurrada"] and r["x"] == 300 and r["y"] == 200 and not r["rejeitada"]
    # a zona ocupa a janela inteira: nenhum lugar livre, a soltura é rejeitada
    r = _m("M.resolver({x:10,y:10,w:100,h:100}, {w:300,h:300}, {x:0,y:0,w:300,h:300})")
    assert r["rejeitada"] is True
    # empurrada para fora da janela pelo lado errado é descartado: sobra o lado livre
    r = _m("M.resolver({x:5,y:100,w:100,h:100}, {w:400,h:300}, {x:0,y:50,w:250,h:200})")
    assert not r["rejeitada"] and r["x"] == 250


@precisa_node
def test_fracao_salva_acompanha_o_redimensionamento():
    f = _m(f"M.dePixels({{x:400,y:250,w:200,h:100}}, {AREA})")
    assert f == {"x": 0.5, "y": 0.5}
    p = _m("M.paraPixels({x:1,y:1}, {w:200,h:100}, {w:500,h:300})")
    assert (p["x"], p["y"]) == (300, 200)  # janela menor: continua dentro


@precisa_node
def test_teclado_passos_e_anuncio():
    assert _m("M.passo('ArrowLeft', false)") == {"dx": -16, "dy": 0}
    assert _m("M.passo('ArrowDown', true)") == {"dx": 0, "dy": 64}
    assert _m("M.passo('a', false)") is None
    assert "50% da esquerda" in _m(f"M.anuncio('Clima', {{x:400,y:250,w:200,h:100}}, {AREA})")


@precisa_node
@pytest.mark.parametrize("bruto", ["null", "'texto'", "[1,2]", "42", "{clima:5}", "{clima:{x:'a',y:0}}", "{clima:{x:2,y:0}}",
                                    "{clima:{x:NaN,y:0}}", "{__proto__:{x:0,y:0},constructor:{x:0,y:0}}", "{naoexiste:{x:0,y:0}}"])
def test_json_corrompido_vira_layout_vazio(bruto):
    assert _m(f"M.sanear({bruto})") == {}


@pytest.mark.parametrize("bruto", [None, "texto", [1], 42, {"clima": 5}, {"clima": {"x": "a", "y": 0}}, {"clima": {"x": 2, "y": 0}},
                                    {"clima": {"x": float("nan"), "y": 0}}, {"clima": {"x": True, "y": 0}}])
def test_ponte_python_recusa_layout_corrompido(bruto):
    assert api_layout.sanear(bruto) == {}


@precisa_node
def test_json_antigo_aproveita_so_o_valido():
    bruto = {"clima": {"x": 0.2, "y": 0.4}, "vagas": {"x": 7, "y": 0}, "lixo": {"x": 0, "y": 0}, "canal": {"x": 1, "y": 0, "extra": "<b>"}}
    assert _m(f"M.sanear({json.dumps(bruto)})") == {"clima": {"x": 0.2, "y": 0.4}, "canal": {"x": 1, "y": 0}}
    assert api_layout.sanear(bruto) == {"clima": {"x": 0.2, "y": 0.4}, "canal": {"x": 1.0, "y": 0.0}}


@precisa_node
def test_ids_iguais_no_python_e_no_js_e_na_pagina():
    assert tuple(_m("M.IDS")) == api_layout.IDS
    pagina = web.page()
    for chave, marca in {"telemetria": 'class="painel tele"', "tecnologia": 'id="cx-tecnologia"', "canal": 'class="canal"', "clima": 'id="cx-clima"'}.items():
        assert marca in pagina, chave


def test_config_antiga_sem_layout_carrega_e_ponte_grava(tmp_path, monkeypatch):
    arquivo = tmp_path / "config.json"
    arquivo.write_text(json.dumps({"user_name": "Ana"}), encoding="utf-8")
    assert config.load(arquivo).layout_caixas == {}
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)

    class Api(LayoutMixin):
        _cfg = SimpleNamespace(layout_caixas={})

    api = Api()
    assert api.set_layout({"clima": {"x": 0.1, "y": 0.2}, "x": "<script>"})["posicoes"] == {"clima": {"x": 0.1, "y": 0.2}}
    assert json.loads(arquivo.read_text(encoding="utf-8"))["layout_caixas"] == {"clima": {"x": 0.1, "y": 0.2}}
    assert api.get_layout()["posicoes"] == {"clima": {"x": 0.1, "y": 0.2}}
    assert api.restaurar_layout()["posicoes"] == {}
    assert api.set_layout("lixo")["posicoes"] == {}


@precisa_node
def test_hora_relativa():
    r = lambda t: _modulo_caixas(f"M.relativo({t}, 10000)")
    assert [r(9990), r(9000), r(6400), _modulo_caixas("M.relativo(100000, 300000)")] == ["agora", "há 16 min", "há 1 h", "há 2 d"]
    assert r(0) == "" and r("null") == "" and r(11000) == "agora"


def _modulo_caixas(expr):
    caminho = json.dumps((JS / "caixas.js").as_posix())
    return json.loads(subprocess.run(["node", "-e", f"const M = require({caminho}); console.log(JSON.stringify({expr}));"],
                                     capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout)


# ── ponte de notícias de tecnologia ──────────────────────────────────────────────────────────────────────

def _rss(*itens):
    corpo = "".join(f"<item><title>{t}</title><link>{l}</link><description>{d}</description><pubDate>{p}</pubDate></item>" for t, l, d, p in itens)
    return f"<rss><channel>{corpo}</channel></rss>".encode()


class _Api(InfoMixin):
    def __init__(self):
        self._cfg = SimpleNamespace(city="x")


def _fixar_agora(monkeypatch, ts=1_800_000_000.0):
    monkeypatch.setattr(api_info, "_agora", lambda: ts)
    return ts


def test_tecnologia_ordena_limpa_e_filtra_links(monkeypatch):
    _fixar_agora(monkeypatch)
    xml = {
        "tecnoblog": _rss(("Novo chip &lt;b&gt;rápido&lt;/b&gt;", "https://tecnoblog.net/a", "<script>alert(1)</script>Resumo", "Fri, 15 Jan 2027 08:00:00 +0000"),
                          ("Golpe", "javascript:alert(1)", "x", "Fri, 15 Jan 2027 07:00:00 +0000")),
        "canaltech": _rss(("Mais recente", "https://canaltech.com.br/b", "r", "Fri, 15 Jan 2027 08:10:00 +0000")),
        "olhardigital": b"<<<isto nao e xml>>>",
    }
    monkeypatch.setattr(api_info.news, "fetch", lambda url, *a, **k: next(v for k, v in xml.items() if k in url))
    r = _Api().info_tecnologia(True)
    assert r["estado"] == "ok" and [i["titulo"] for i in r["itens"]][0] == "Mais recente"
    todos = json.dumps(r, ensure_ascii=False)
    assert "<script>" not in todos and "alert(1)" not in todos.replace("javascript:alert(1)", "")
    golpe = next(i for i in r["itens"] if i["titulo"] == "Golpe")
    assert golpe["link"] == ""  # só http/https
    assert all(i["quando"] > 0 and i["fonte"] for i in r["itens"])


def test_tecnologia_falha_de_rede_da_erro_amigavel_e_reaproveita_cache(monkeypatch):
    _fixar_agora(monkeypatch)
    api = _Api()

    def cai(*a, **k):
        raise OSError("sem rede")

    monkeypatch.setattr(api_info.news, "fetch", cai)
    r = api.info_tecnologia(True)
    assert r["estado"] == "erro" and r["itens"] == [] and "Traceback" not in json.dumps(r)
    monkeypatch.setattr(api_info.news, "fetch", lambda *a, **k: _rss(("Boa", "https://a.b/c", "", "Fri, 15 Jan 2027 08:00:00 +0000")))
    assert api.info_tecnologia(True)["estado"] == "ok"
    monkeypatch.setattr(api_info.news, "fetch", cai)
    antigo = api.info_tecnologia(True)  # rede caiu depois: última leitura boa, avisando
    assert antigo["itens"] and antigo["desatualizado"] is True


def test_tecnologia_nao_repete_titulo_e_limita(monkeypatch):
    _fixar_agora(monkeypatch)
    itens = [(f"Título {n}", f"https://a.b/{n}", "", f"Fri, 15 Jan 2027 0{n % 8}:00:00 +0000") for n in range(9)]
    monkeypatch.setattr(api_info.news, "fetch", lambda *a, **k: _rss(*itens, itens[0]))
    r = _Api().info_tecnologia(True)
    assert len(r["itens"]) <= api_info.MAX_TEC
    assert len({i["titulo"] for i in r["itens"]}) == len(r["itens"])


# ── contrato estático ────────────────────────────────────────────────────────────────────────────────────

def test_arrastar_e_layout_sem_innerhtml_cor_fixa_ou_recurso_externo():
    for nome in ("arrastar.js", "layout-salvo.js"):
        texto = (JS / nome).read_text(encoding="utf-8")
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|eval\(|document\.write", texto), nome
        assert not re.search(r"https?://", texto)
    css = (CSS / "arrastar.css").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", css) and not re.search(r"\b(?:rgb|hsl)a?\(\s*\d", css)
    assert "prefers-reduced-motion" in css and "touch-action: none" in css
    assert "http" not in css


def test_ordem_dos_arquivos_da_pagina():
    assert web.CSS[-1] == "design" and "arrastar" in web.CSS
    assert web.JS.index("layout-salvo") < web.JS.index("arrastar") < web.JS.index("main")
    pagina = web.page()
    assert 'id="layout-padrao"' in pagina and 'id="cx-tecnologia"' in pagina
    assert "setPointerCapture" in pagina and "Restaurar layout" in pagina
    assert "innerHTML" not in (JS / "caixas.js").read_text(encoding="utf-8")
