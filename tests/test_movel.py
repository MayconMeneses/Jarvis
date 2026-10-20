"""Jarvis independente do celular (movel/): os testes de JavaScript rodam com node; aqui ficam as conferências com o PC."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from jarvis.dev.ux import cores

MOVEL = Path(__file__).resolve().parent.parent / "movel"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node não está instalado")


def node(codigo: str) -> str:
    saida = subprocess.run([NODE, "--input-type=module", "-e", codigo], capture_output=True, text=True, encoding="utf-8", cwd=MOVEL, timeout=60)
    assert saida.returncode == 0, saida.stderr
    return saida.stdout.strip()


def test_node_test_suites_pass():
    arquivos = [str(p) for p in sorted((MOVEL / "testes").glob("*.test.mjs"))]
    ambiente = {**os.environ, "PYTHON": sys.executable}  # os testes de paridade (modelos, zip) comparam com o Python do projeto
    saida = subprocess.run([NODE, "--test", *arquivos], capture_output=True, text=True, encoding="utf-8", timeout=240, env=ambiente, cwd=MOVEL.parent)
    assert saida.returncode == 0, saida.stdout[-3000:] + saida.stderr[-1000:]


def test_knowledge_file_is_up_to_date_with_the_pc_data():
    """Uma fonte só: se a base do PC mudar, rode `python movel/gerar_dados.py`."""
    assert subprocess.run([sys.executable, str(MOVEL / "gerar_dados.py"), "--conferir"], capture_output=True).returncode == 0


def test_design_tools_match_the_python_versions():
    amostra = ["#3b82f6", "#767676", "#ff9a3c", "#00e5ff", "#808080"]
    js = json.loads(node(
        'import * as d from "./js/design.js";'
        f"const cores = {json.dumps(amostra)};"
        "console.log(JSON.stringify({paleta: cores.map(d.paleta), contraste: cores.map((c) => d.contraste(c, '#ffffff')),"
        "escala: d.escalaTipografica(16, 1.25), tokens: d.tokensCss('#3b82f6')}));"))
    assert js["paleta"] == [cores.paleta(c) for c in amostra]
    assert js["contraste"] == pytest.approx([cores.contraste(c, "#ffffff") for c in amostra])
    assert js["escala"] == [[n, t] for n, t in cores.escala_tipografica(16, 1.25)]
    assert js["tokens"] == cores.tokens_css("#3b82f6")


def test_generators_match_the_python_versions():
    from jarvis.dev import gerar

    js = json.loads(node(
        'import * as g from "./js/gerar.js";'
        "console.log(JSON.stringify({sql: g.esquemaSql('pedidos', {total: 'decimal', status: 'texto'}, {cliente_id: 'clientes'}),"
        "api: g.openapi('Loja', ['clientes', 'pedidos']), ci: g.workflowCi('node'), dock: g.dockerfile('python', 8000), ed: g.editorconfig()}));"))
    assert js["sql"] == gerar.esquema_sql("pedidos", {"total": "decimal", "status": "texto"}, {"cliente_id": "clientes"})
    assert js["api"] == gerar.openapi("Loja", ["clientes", "pedidos"])
    assert js["ci"] == gerar.workflow_ci("node") and js["dock"] == gerar.dockerfile("python", 8000) and js["ed"] == gerar.editorconfig()


def test_service_worker_caches_only_files_that_exist():
    texto = (MOVEL / "sw.js").read_text(encoding="utf-8")
    lista = re.search(r"const CASCA = \[(.*?)\];", texto, re.S).group(1)
    for caminho in re.findall(r'"([^"]+)"', lista):
        assert caminho == "./" or (MOVEL / caminho).is_file(), caminho  # um arquivo faltando derruba a instalação inteira do service worker
    for arquivo in (MOVEL / "js").glob("*.js"):
        assert f"js/{arquivo.name}" in lista, f"{arquivo.name} não está no cache offline"


def test_page_is_installable_safe_and_runs_no_inline_script():
    html = (MOVEL / "index.html").read_text(encoding="utf-8")
    for exigido in ("apple-mobile-web-app-capable", "apple-touch-icon", 'rel="manifest"', "viewport-fit=cover", 'lang="pt-BR"', "Content-Security-Policy"):
        assert exigido in html, exigido
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", html), "sem script inline: a política de segurança não permite"
    assert not re.search(r"(?<!wasm-)unsafe-eval", html) and "script-src 'self' https://cdn.jsdelivr.net" in html
    manifesto = json.loads((MOVEL / "manifest.webmanifest").read_text(encoding="utf-8"))
    assert manifesto["display"] == "standalone" and manifesto["lang"] == "pt-BR"
    for icone in manifesto["icons"]:
        assert (MOVEL / icone["src"]).is_file()
    assert "16px" in (MOVEL / "css" / "app.css").read_text(encoding="utf-8")  # o iPhone não dá zoom em campos de 16px


def test_everything_runs_on_the_phone_without_the_pc():
    """Nada no app do celular aponta para o PC, para um servidor próprio ou para a API do Jarvis do PC."""
    for arquivo in (MOVEL / "js").glob("*.js"):
        texto = arquivo.read_text(encoding="utf-8")
        assert not re.search(r"[\"'`]/api/", texto) and "192.168" not in texto and "localhost" not in texto, arquivo.name
    destinos = set()
    for arquivo in (MOVEL / "js").glob("*.js"):
        destinos |= set(re.findall(r"https://([a-z0-9.\-]+)", arquivo.read_text(encoding="utf-8")))
    assert destinos <= {"pt.wikipedia.org", "cdn.jsdelivr.net", "generativelanguage.googleapis.com", "api.openai.com", "api.groq.com", "openrouter.ai", "seu-proxy.workers.dev", "geocoding-api.open-meteo.com", "api.open-meteo.com", "api.rss2json.com", "hacker-news.firebaseio.com", "news.ycombinator.com", "api.github.com", "remotive.com", "g1.globo.com", "feeds.bbci.co.uk", "agenciabrasil.ebc.com.br", "tecnoblog.net", "canaltech.com.br", "olhardigital.com.br", "github.com"}, destinos  # só Wikipédia, a biblioteca do cérebro e os provedores que o usuário cadastrar


def test_stack_and_habilidades_text_matches_the_pc():
    """Mesmos textos do PC: tecnologias, comparação, visão por área, recomendação e checklist de habilidades."""
    from jarvis.dev import conhecimento, habilidades

    js = json.loads(node(
        'import { readFileSync } from "node:fs"; import { Saber } from "./js/saber.js"; import { Stack } from "./js/stack.js"; import { Habilidades } from "./js/habilidades.js";'
        'const d = JSON.parse(readFileSync("./dados/saber.json", "utf8")); const s = new Saber(d); const st = new Stack(d.tecnologias, d.tipos); const h = new Habilidades(d.habilidades, s);'
        'const r = st.tecnologias.find((t) => t.id === "react"), v = st.tecnologias.find((t) => t.id === "vue");'
        'console.log(JSON.stringify({desc: st.descrever(r), comp: st.comparar(r, v), area: st.visaoGeral("back end"), tipos: st.visaoTipos(), check: h.checklist("segurança"), geral: h.visaoGeral()}));'))
    assert js["desc"] == conhecimento.describe(conhecimento.lookup("react"))
    assert js["comp"] == conhecimento.compare(conhecimento.lookup("react"), conhecimento.lookup("vue"))
    assert js["area"] == conhecimento.overview("back end") and js["tipos"] == conhecimento.types_overview()
    assert js["check"] == habilidades.checklist("segurança") and js["geral"] == habilidades.visao_geral().replace(" (medido automaticamente)", "")  # o celular não mede projetos
