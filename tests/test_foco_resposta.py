"""Modo foco do PC: orbe central, resposta em Markdown por DOM (md.js) e painel rolável."""

from jarvis.ui import web


def test_foco_esta_na_pagina_e_design_continua_o_ultimo_css():
    assert web.CSS[-1] == "design" and "foco-tela" in web.CSS
    assert web.JS.index("md") < web.JS.index("foco-resposta") < web.JS.index("face")
    html = web.page()
    for trecho in ('id="foco-resp"', 'id="foco-resp-painel"', 'id="foco-resp-mais"', "window.FocoResposta", "window.Md"):
        assert trecho in html


def test_resposta_do_foco_nao_usa_html_cru():
    for nome in ("md.js", "foco-resposta.js"):
        codigo = (web.BASE / "js" / nome).read_text(encoding="utf-8")
        assert not any(p in codigo for p in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write"))
