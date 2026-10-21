"""Janela do PC: estrutura da página, barra de botões, tokens de cor, estados de erro e regras puras dos canvases."""

import json
import re
import shutil
import subprocess

import pytest

from jarvis.ui import web
from test_tema import _contraste, _tokens  # mesmas contas de contraste dos temas

CSS = web.BASE / "css"
JS = web.BASE / "js"
precisa_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")


def _ler(caminho):
    return caminho.read_text(encoding="utf-8")


def test_pagina_tem_um_unico_main_e_o_log_dentro_dele():
    html = web.page()
    assert html.count("<main") == 1  # os diálogos e o modo foco não criam outro marco "main"
    principal = html.split('<main id="principal"')[1].split("</main>")[0]
    assert 'id="log" role="log"' in principal and 'id="orbe"' in principal and 'id="form"' in principal


def test_menu_reune_todas_as_acoes_e_a_barra_de_botoes_sumiu():
    html = _ler(web.BASE / "index.html")
    assert "<nav" not in html and 'class="toolbar"' not in html  # nenhuma barra de botões solta
    topo = html.split('<header class="topo">')[1].split("</header>")[0]
    menu = topo.split('id="tb-mais-menu"')[1]
    assert len(re.findall(r"<button", topo.split('id="tb-mais-menu"')[0])) == 1  # só o botão do menu fora dele
    for botao in ("open-face", "bom-dia", "open-agentes", "open-memory", "open-brains", "open-oficina", "open-agenda", "open-uso", "reset"):
        assert f'id="{botao}"' in menu
    assert 'aria-haspopup="menu"' in topo and 'aria-expanded="false"' in topo and 'aria-controls="tb-mais-menu"' in topo
    assert "toolbar" in web.CSS and "toolbar" in web.JS and "menu-nav" in web.JS


def test_todo_id_usado_pelos_scripts_existe_na_pagina():
    html = web.page()
    ids = set(re.findall(r'\bid="([\w-]+)"', html))
    usados = set()
    for arquivo in web.JS:
        usados |= set(re.findall(r'getElementById\("([\w-]+)"\)', _ler(JS / f"{arquivo}.js")))
    dinamicos = {"suggestions", "ag-d-idade", "ag-d-prox", "ag-rodar"}  # criados em tempo de execução
    faltando = {i for i in usados - ids - dinamicos if not i.startswith(("g-", "v-", "fp-", "key-", "fb-", "uso-c-", "mem-aba"))}
    assert not faltando, faltando


def test_cores_so_em_tokens_nos_css_e_nos_canvases():
    cor_fixa = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d")
    for css in CSS.glob("*.css"):
        if css.stem in ("base", "design"):  # só estes dois definem os valores dos temas
            continue
        texto = re.sub(r"/\*.*?\*/", "", _ler(css), flags=re.S)
        assert not cor_fixa.search(texto), f"cor fixa em {css.name}"
    for nome in ("memory-grafo", "uso-graficos", "agents-desenho", "face-paineis", "face", "orbe", "orbe-filamentos"):
        assert not cor_fixa.search(_ler(JS / f"{nome}.js")), f"cor fixa em {nome}.js"


def test_sem_innerhtml_nem_recurso_externo_na_janela():
    for arquivo in list(JS.glob("*.js")) + list(CSS.glob("*.css")) + list(web.BASE.glob("*.html")):
        texto = _ler(arquivo)
        assert "innerHTML" not in texto and "insertAdjacentHTML" not in texto, arquivo.name
        assert "@import" not in texto and "<link" not in texto and not re.search(r'(?:src|href)="https?:', texto), arquivo.name


def test_movimento_reduzido_cobre_o_fundo_dos_dialogos():
    css = _ler(CSS / "design.css")
    assert re.search(r"prefers-reduced-motion: reduce\) \{\s*\*, \*::before, \*::after, dialog::backdrop", css)
    assert 'data-efeitos="desligado"] dialog::backdrop' in css


@pytest.mark.parametrize("tema", ["hud", "ambar", "esmeralda", "contraste"])
def test_texto_sobre_o_destaque_tem_contraste_aa(tema):
    t = _tokens()[tema]
    assert _contraste(t["on-accent"], t["cyan"]) >= 4.5  # botão primário e microfone gravando


def test_mensagens_de_erro_conhecidas_sao_humanas():
    messages = _ler(JS / "messages.js")
    for trecho in ("Sem conexão com a internet.", "A resposta demorou demais.", "A chave de acesso foi recusada."):
        assert trecho in messages


def test_dialogos_tem_estado_de_erro_e_vazio():
    assert "Nada guardado ainda" in _ler(JS / "memory.js") and "Nenhuma nota encontrada" in _ler(JS / "memory.js")
    assert "Não consegui ler o uso agora" in _ler(JS / "uso.js")
    assert "Não consegui falar com a Jarvis" in _ler(JS / "oficina.js") and "Nenhum agente cadastrado" in _ler(JS / "agents.js")


def _node(codigo):
    saida = subprocess.run(["node", "-e", codigo], capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout
    return json.loads(saida)


@precisa_node
def test_cores_do_tema_alfa_e_serie_de_graficos():
    caminho = json.dumps((JS / "cores.js").as_posix())
    codigo = ("global.window = { addEventListener() {} }; global.document = {};"
              f"eval(require('fs').readFileSync({caminho}, 'utf8'));"
              "const C = window.Cores; console.log(JSON.stringify([C.alfa('rgb(1, 2, 3)', 0.5), C.alfa('#fff', 1)]));")
    assert _node(codigo) == ["rgba(1, 2, 3, 0.5)", "#fff"]


@precisa_node
def test_formato_brasileiro_dos_numeros_de_uso():
    trecho = re.search(r"const usoDec = .*?\n  function usoNum.*?\n  function usoUsd.*?\n", _ler(JS / "uso.js"), re.S).group(0)
    codigo = trecho + "console.log(JSON.stringify([usoUsd(1234.5), usoNum(90000), usoNum(12), usoNum(2500000)]));"
    assert _node(codigo) == ["US$ 1.234,50", "90,0 k", "12", "2,50 M"]
