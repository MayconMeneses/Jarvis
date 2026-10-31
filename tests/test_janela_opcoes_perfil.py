"""Janela do PC: botões do "Você quis dizer", atalhos sem cérebro, tela Meu perfil e ferramentas externas (só pedem, nunca executam)."""

import json
import re
import shutil
import subprocess

import pytest

from jarvis.ui import web
from jarvis.ui.api import Api

JS = web.BASE / "js"
precisa_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")
NOVOS = ("opcoes", "atalhos", "perfil", "ferramentas")


def _node(expressao: str):
    caminho = (JS / "opcoes.js").as_posix()
    codigo = f"const O = require({json.dumps(caminho)}); console.log(JSON.stringify({expressao}));"
    saida = subprocess.run(["node", "-e", codigo], capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout
    return json.loads(saida)


TEXTO = "Você quis dizer:\\n1. fazer backup do PC\\n2. fazer backup do celular\\n3. restaurar\\nResponda 1, 2 ou 3 (ou “não”)."


@precisa_node
def test_extrai_ate_tres_opcoes_do_voce_quis_dizer():
    r = _node(f'O.extrair("{TEXTO}")')
    assert [o["n"] for o in r] == [1, 2, 3] and r[1]["rotulo"] == "fazer backup do celular"


@precisa_node
@pytest.mark.parametrize("texto", ["1. uma lista qualquer\\n2. sem pergunta", "", "Responda 1 mas sem lista"])
def test_texto_que_nao_e_a_pergunta_nao_vira_botao(texto):
    assert _node(f'O.extrair("{texto}")') == []


@precisa_node
def test_rotulo_enorme_e_cortado_e_so_ha_tres_botoes():
    longo = "x" * 500
    r = _node(f'O.extrair("1. {longo}\\n2. b\\n3. c\\n4. d\\nResponda 1")')
    assert len(r) == 3 and len(r[0]["rotulo"]) == 80


@precisa_node
def test_pesquisa_reaproveita_o_pedido_original():
    assert _node('O.pesquisa("  como   faço backup  ")') == "pesquisa como faço backup"
    assert _node('O.pesquisa("")') == ""


@precisa_node
def test_atalhos_aceitam_so_acao_conhecida_e_http():
    r = _node('O.atalhos([{rotulo:"A",acao:"cerebros"},{rotulo:"B",url:"https://aistudio.google.com/apikey"},'
              '{rotulo:"C",url:"javascript:alert(1)"},{rotulo:"D",url:"file:///c:/x"},{rotulo:"E",acao:"apagar"},{url:"https://x.y"},null])')
    assert [a["rotulo"] for a in r] == ["A", "B"] and r[0]["tipo"] == "acao" and r[1]["tipo"] == "url"
    assert _node("O.atalhos(undefined)") == []


def test_novos_arquivos_na_ordem_certa_e_design_continua_por_ultimo():
    assert web.CSS[-1] == "design"
    assert all(n in web.JS for n in NOVOS) and web.JS.index("opcoes") < web.JS.index("main")
    html = web.page()
    for ident in ("open-perfil", "perfil", "pf-lista", "ft-lista", "ft-info", "close-perfil"):
        assert f'id="{ident}"' in html


def test_novos_scripts_sem_innerhtml_e_sem_cor_fixa():
    cor_fixa = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d")
    for nome in NOVOS:
        js = (JS / f"{nome}.js").read_text(encoding="utf-8")
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(", js), nome
    for css in ("atalhos", "perfil", "ferramentas"):
        assert not cor_fixa.search((web.BASE / "css" / f"{css}.css").read_text(encoding="utf-8")), css


def test_perfil_avisa_o_que_nunca_e_guardado():
    texto = (web.BASE / "perfil.html").read_text(encoding="utf-8")
    for palavra in ("senhas", "documentos", "dinheiro", "saúde"):
        assert palavra in texto


def test_ferramentas_avisam_que_so_pedem():
    texto = (web.BASE / "brains.html").read_text(encoding="utf-8")
    assert "apenas <b>pedem</b>" in texto and "Aprovar" in texto
    assert 'id="close-brains"' in texto


# ── ponte com mocks: tudo vira cartão, nada executa ──────────────────────────

class _Loja:
    def __init__(self):
        self.salvas = []

    def save(self, acao):
        self.salvas.append(acao)
        return acao

    def pending_since(self, desde):
        return list(self.salvas)


class _Memoria:
    def get(self, ref):
        return None

    def list_notes(self, prefixo="", limite=500):
        return []

    def memories(self):
        return []


def _api():
    api = object.__new__(Api)
    api._store, api._memory = _Loja(), _Memoria()
    from jarvis.config import Config
    api._cfg = Config()
    return api


def test_perfil_definir_e_apagar_geram_cartao_sem_gravar():
    api = _api()
    r = api.perfil_definir("tom", "direto e curto")
    assert r["actions"][0]["descricao"].startswith("Atualizar seu perfil?") and api._store.salvas[0].kind == "atualizar_perfil"
    assert "error" in api.perfil_definir("senha", "123")  # campo fora da lista
    assert "error" in api.perfil_apagar("tom")  # nada definido para apagar


def test_perfil_usuario_lista_os_campos_com_origem():
    campos = _api().perfil_usuario()["campos"]
    assert campos["quem"]["origem"] == "deduzido" and campos["quem"]["nome"] == "Quem sou"


def test_ferramentas_listam_o_catalogo_com_permissoes_e_risco():
    itens = _api().ferramentas_externas()
    assert itens and all({"nome", "versao", "descricao", "permissoes", "riscos", "risco", "instalada", "ativa"} <= set(i) for i in itens)


def test_ferramenta_pedir_acao_invalida_nao_cria_cartao():
    api = _api()
    r = api.ferramenta_externa_pedir("executar", "tempo")
    assert r["ok"] is False and not api._store.salvas
