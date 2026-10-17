"""Engenharia, arquitetura, sistemas, UX, padrões de projeto e geradores: dados completos e código EXECUTADO."""

import json
import shutil
import sqlite3
import subprocess

import pytest

from jarvis.dev import engenharia, gerar, logica, saber, ux
from jarvis.dev.ux import cores

PADROES = (*engenharia.padroes(), *engenharia.estruturas())  # padrões de projeto e estruturas de dados, mesmo formato e mesmo teste
NODE = shutil.which("node")
CAMPOS = ("resumo", "passos", "analogia", "exemplo", "erros", "exercicios")


def test_topics_are_complete_and_ids_unique():
    todos = [*engenharia.itens(), *ux.itens()]
    assert len(engenharia.itens()) >= 29 and len(ux.itens()) >= 14
    ids = [t["id"] for t in [*todos, *logica.conceitos()]]
    assert len(ids) == len(set(ids))
    for t in todos:
        assert all(t.get(c) for c in CAMPOS) and t["aliases"], t["id"]


@pytest.mark.parametrize("termo, tipo, id_", [
    ("SOLID", "engenharia", "solid"), ("arquitetura hexagonal", "engenharia", None), ("heurísticas de Nielsen", "ux", None),
    ("acessibilidade", "ux", None), ("recursão", "logica", "recursao"), ("strategy", "padrao", "strategy"),
])
def test_unified_lookup(termo, tipo, id_):
    achado = saber.procurar(termo)
    assert achado and achado[0] == tipo
    if id_:
        assert achado[1]["id"] == id_


def test_unified_lookup_unknown_and_explain():
    assert saber.procurar("receita de bolo") is None and saber.explicar("receita de bolo") is None
    assert "Como aplicar" in saber.explicar("SOLID") and "```python" in saber.explicar("observer")
    assert "Strategy" in saber.explicar("estratégia padrão strategy") and saber.total()["padroes"] >= 8
    assert {k for k, _ in saber.citados("SOLID e acessibilidade e recursão")} == {"engenharia", "ux", "logica"}


# ── padrões de projeto ───────────────────────────────────────────────────

def test_pattern_library_is_complete():
    assert len(engenharia.padroes()) >= 8 and len(engenharia.estruturas()) >= 9
    for p in PADROES:
        assert {"nome", "problema", "ideia", "pseudocodigo", "codigo", "casos", "funcoes"} <= set(p), p["id"]
        assert set(p["codigo"]) == {"python", "javascript"} and len(p["ideia"]) >= 3 and p["casos"], p["id"]
        assert p["problema"].startswith("Quando usar") or p in engenharia.estruturas(), p["id"]


@pytest.mark.parametrize("p", PADROES, ids=lambda p: p["id"])
def test_python_pattern_passes(p):
    espaco: dict = {}
    exec(p["codigo"]["python"], espaco)  # nosec: código da própria biblioteca
    for args, esperado in p["casos"]:
        assert espaco[p["funcoes"]["python"]](*args) == esperado, p["id"]


@pytest.mark.skipif(NODE is None, reason="node não está instalado")
@pytest.mark.parametrize("p", PADROES, ids=lambda p: p["id"])
def test_javascript_pattern_passes(p, tmp_path):
    funcao = p["funcoes"]["javascript"]
    chamadas = ", ".join(f"{funcao}(...{json.dumps(args)})" for args, _ in p["casos"])
    arquivo = tmp_path / "t.js"
    arquivo.write_text(p["codigo"]["javascript"] + f"\nconsole.log(JSON.stringify([{chamadas}]));\n", encoding="utf-8")
    saida = subprocess.run([NODE, str(arquivo)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert saida.returncode == 0, saida.stderr
    assert json.loads(saida.stdout) == [esperado for _, esperado in p["casos"]], p["id"]


def test_pattern_lookup_and_show():
    assert engenharia.padrao("quero desfazer e refazer")["id"] == "command"
    assert engenharia.padrao("padrão repository")["id"] == "repository"
    assert engenharia.padrao("clima de hoje") is None
    texto = engenharia.mostrar_padrao(engenharia.padrao("observer"), "javascript")
    assert "```javascript" in texto and "Pseudocódigo" in texto
    assert "Tenho este padrão em" in engenharia.mostrar_padrao(engenharia.padrao("observer"), "go")
    assert "Observer" in engenharia.visao_padroes()


# ── UX ───────────────────────────────────────────────────────────────────

def test_contrast_matches_wcag_reference_values():
    assert cores.contraste("#000", "#fff") == pytest.approx(21.0)
    assert cores.contraste("#767676", "#ffffff") == pytest.approx(4.54, abs=0.01)
    assert cores.contraste("#777777", "#ffffff") < 4.5 <= cores.contraste("#767676", "#ffffff")
    assert "FALHA" in cores.avaliar_contraste("#999", "#fff") and "passa" in cores.avaliar_contraste("#000", "#fff")
    with pytest.raises(ValueError):
        cores.para_rgb("azul")


def test_palette_scale_and_tokens():
    tons = cores.paleta("#3b82f6")
    assert list(tons) == ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900"]
    assert cores.luminancia(tons["50"]) > cores.luminancia(tons["500"]) > cores.luminancia(tons["900"])
    assert cores.escala_tipografica(16, 1.25)[2] == ("base", 16.0) and cores.escala_tipografica()[3] == ("lg", 20.0)
    assert cores.escala_espacamento()[:3] == [4, 8, 12]
    css = cores.tokens_css("#3b82f6")
    assert css.count("{") == css.count("}") and "--cor-500" in css and "prefers-reduced-motion" in css
    assert "700" in cores.relatorio_paleta("#3b82f6") and "razão" in cores.relatorio_escala()


# ── geradores ────────────────────────────────────────────────────────────

def test_sql_schema_runs_in_sqlite():
    banco = sqlite3.connect(":memory:")
    banco.executescript(gerar.esquema_sql("clientes", {"nome": "texto", "idade": "inteiro"}))
    banco.executescript(gerar.esquema_sql("pedidos", {"total": "decimal"}, {"cliente_id": "clientes"}))
    banco.execute("INSERT INTO clientes(nome, idade) VALUES ('Ana', 30)")
    banco.execute("INSERT INTO pedidos(total, cliente_id) VALUES (9.5, 1)")
    assert banco.execute("SELECT COUNT(*) FROM pedidos").fetchone() == (1,)
    with pytest.raises(ValueError):
        gerar.esquema_sql("1; DROP TABLE x", {})


def test_openapi_is_valid_yaml():
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(gerar.openapi("Loja", ["clientes", "pedidos"]))
    assert doc["openapi"].startswith("3") and set(doc["paths"]) == {"/clientes", "/clientes/{id}", "/pedidos", "/pedidos/{id}"}
    assert set(doc["paths"]["/clientes"]) == {"get", "post"}


def test_ci_dockerfile_adr_story_editorconfig():
    yaml = pytest.importorskip("yaml")
    for lang in ("python", "node", "go", "js"):
        assert yaml.safe_load(gerar.workflow_ci(lang))["jobs"]["testes"]["steps"]
    with pytest.raises(ValueError):
        gerar.workflow_ci("cobol")
    assert "USER app" in gerar.dockerfile("python") and "USER node" in gerar.dockerfile("node", 3000) and "3000" in gerar.dockerfile("js", 3000)
    adr = gerar.adr("Usar SQLite", "Preciso de um banco simples.", "Adotar SQLite.", numero=3)
    assert adr.startswith("# ADR 0003: Usar SQLite") and "## Contexto" in adr and "## Decisão" in adr
    historia = gerar.historia_usuario("cliente", "pagar com Pix", "finalizar a compra rápido", ["Gera QR code"])
    assert "**Como** cliente" in historia and "- [ ] Gera QR code" in historia
    assert "root = true" in gerar.editorconfig()


# ── novas checagens de projeto ───────────────────────────────────────────

def _projeto(tmp_path, arquivos):
    from jarvis.dev.habilidades import varredura

    for caminho, texto in arquivos.items():
        alvo = tmp_path / caminho
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")
    return varredura.escanear(tmp_path)


def test_architecture_check_finds_import_cycles(tmp_path):
    from jarvis.dev.habilidades import checagens_design as D

    ruim = _projeto(tmp_path / "ruim", {"app/a.py": "import app.b\n", "app/b.py": "from app import a\nimport app.c\n", "app/c.py": "x = 1\n"})
    assert D.ciclos(ruim) == [["app.a", "app.b"]]
    resultado = D.arquitetura(ruim)
    assert any("ciclo" in a for a in resultado.achados) and any("Quebre o ciclo" in s for s in resultado.sugestoes)
    bom = _projeto(tmp_path / "bom", {"app/a.py": "import app.b\n", "app/b.py": "x = 1\n", "docs/adr/0001.md": "# ADR\n"})
    assert D.ciclos(bom) == [] and D.arquitetura(bom).nota == 100
    assert D.arquitetura(_projeto(tmp_path / "um", {"a.py": "x = 1\n"})).nota is None


def test_interface_design_check(tmp_path):
    from jarvis.dev.habilidades import checagens_design as D

    pobre = _projeto(tmp_path / "pobre", {"estilo.css": "a { outline: none; transition: all 1s; width: 300px }"})
    r = D.design_de_interface(pobre)
    assert r.nota < 30 and any("variáveis" in s for s in r.sugestoes) and any("movimento" in s.lower() or "reduced-motion" in s for s in r.sugestoes)
    rico = _projeto(tmp_path / "rico", {"estilo.css": (":root { --cor: #123; } a { color: var(--cor); font-size: 1rem; transition: color 1s }\n"
                                                      "a:focus-visible { outline: 2px solid }\n@media (min-width: 600px) { a { margin: 0 } }\n"
                                                      "@media (prefers-color-scheme: dark) { :root { --cor: #fff } }\n"
                                                      "@media (prefers-reduced-motion: reduce) { a { transition: none } }")})
    assert D.design_de_interface(rico).nota == 100
    assert D.design_de_interface(_projeto(tmp_path / "vazio", {"a.py": "x = 1\n"})).nota is None


# ── motor próprio e ferramentas MCP ──────────────────────────────────────

@pytest.fixture
def motor():
    from jarvis.local.engine import LocalEngine

    return LocalEngine(load_config=lambda: None, brave_key=lambda: None)


@pytest.mark.parametrize("texto, intencao", [
    ("mostre o padrão Observer em JavaScript", "padrao"), ("quais padrões de projeto você sabe", "padrao"),
    ("contraste #767676 sobre #ffffff", "ux_ferramenta"), ("paleta a partir de #3b82f6", "ux_ferramenta"),
    ("escala tipográfica", "ux_ferramenta"), ("tokens css para #3b82f6", "ux_ferramenta"),
    ("crie uma tabela clientes com nome texto, idade inteiro", "gerar"), ("gere um dockerfile para node", "gerar"),
    ("explique SOLID", "tecnologia"), ("o que é arquitetura hexagonal", "tecnologia"),
    ("compare monólito e microsserviços", "comparar"), ("crie um sistema chamado Loja", "criar_sistema"),
])
def test_engine_routes_engineering_requests(motor, texto, intencao):
    assert motor.classify(texto)[0] == intencao


def test_engine_answers_engineering_requests_without_ai(motor):
    assert "```javascript" in motor.handle("mostre o padrão Observer em JavaScript")
    assert "Strategy" in motor.handle("quais padrões de projeto você sabe") and "Observer" in motor.handle("quais padrões de projeto você sabe")
    assert "4.54" in motor.handle("contraste #767676 sobre #ffffff").replace(",", ".") and "FALHA" in motor.handle("contraste #999 sobre #fff")
    assert "--cor-500" in motor.handle("tokens css para #3b82f6") and "Escala tipográfica" in motor.handle("escala tipográfica")
    assert "CREATE TABLE clientes" in motor.handle("crie uma tabela clientes com nome texto, idade inteiro")
    assert "USER node" in motor.handle("gere um dockerfile para node") and "FROM python" in motor.handle("gere um dockerfile")
    assert "Como aplicar" in motor.handle("explique SOLID") and "hexagonal" in motor.handle("o que é arquitetura hexagonal")
    assert "×" in motor.handle("compare monólito e microsserviços")
    assert "heurísticas" in motor.handle("quais conceitos você sabe").lower() and "Observer" in motor.handle("quais conceitos você sabe")


def test_mcp_tools():
    from jarvis.mcp_tools import engenharia_tools as T

    assert "Como aplicar" in T.explicar_topico_de_engenharia("DDD") and "```python" in T.explicar_topico_de_engenharia("Strategy")
    assert "```javascript" in T.explicar_topico_de_engenharia("Strategy", "js") and "Não tenho" in T.explicar_topico_de_engenharia("xadrez")
    assert "Padrões de projeto" in T.listar_o_que_a_jarvis_sabe()
    assert "21.00" in T.avaliar_contraste("#000", "#fff") and "cor inválida" in T.avaliar_contraste("azul", "#fff")
    assert "--cor-500" in T.gerar_tokens_de_design("#3b82f6") and "cor inválida" in T.gerar_tokens_de_design("zzz")
    assert "CREATE TABLE" in T.gerar_artefato("sql", "pedidos", "total decimal, status") and "# ADR" in T.gerar_artefato("adr", "Usar SQLite")
    assert "Como" in T.gerar_artefato("historia", "", "cliente|pagar com Pix|fechar a compra") and "openapi" in T.gerar_artefato("openapi", "Loja", "clientes")
    assert "jobs" in T.gerar_artefato("ci", "node") and "FROM" in T.gerar_artefato("dockerfile", "python") and "root" in T.gerar_artefato("editorconfig")
    assert "linguagem sem modelo" in T.gerar_artefato("ci", "cobol") and "Tipos" in T.gerar_artefato("xyz")
