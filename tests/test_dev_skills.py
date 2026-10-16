"""Habilidades de programação do motor próprio (sem IA) e as ferramentas MCP correspondentes."""

import pytest

from jarvis.config import Config
from jarvis.local.engine import LocalEngine
from jarvis.pc import actions


@pytest.fixture
def cfg(tmp_path):
    return Config(memoria_db=str(tmp_path / "m.db"))


@pytest.fixture
def engine(cfg):
    return LocalEngine(load_config=lambda: cfg, brave_key=lambda: None)


def kind(engine, text):
    found = engine.classify(text)
    return found[0] if found else None


@pytest.mark.parametrize("text, intent", [
    ("o que é React?", "tecnologia"), ("explique recursão", "tecnologia"), ("fale sobre Python", "tecnologia"),
    ("compare Django e FastAPI", "comparar"), ("qual a diferença entre pilha e fila", "comparar"),
    ("qual stack para uma loja virtual?", "recomendar"), ("quais linguagens para back end?", "recomendar"),
    ("como fazer busca binária em Java", "algoritmo"), ("escreva um fatorial em Go", "algoritmo"),
    ("como resolver um problema de programação", "logica"), ("quais algoritmos você sabe", "logica"),
    ("crie um sistema chamado Loja com FastAPI e React", "criar_sistema"),
])
def test_programming_requests_are_classified(engine, text, intent):
    assert kind(engine, text) == intent


def test_existing_commands_are_not_stolen(engine):
    assert kind(engine, "abre o WhatsApp") == "abrir" and kind(engine, "como está o PC?") == "pc"
    assert kind(engine, "pesquise sobre Docker") == "pesquisa" and kind(engine, "que horas são?") == "hora"
    assert kind(engine, "crie um dashboard de C:\\x\\v.csv") == "dashboard" and kind(engine, "quero vagas remotas") == "vagas"


def test_technology_and_concept_answers_come_from_the_knowledge_base(engine, monkeypatch):
    from jarvis.local import websearch

    monkeypatch.setattr(websearch, "research", lambda *a, **k: pytest.fail("não deve ir para a internet"))
    assert "**React**" in engine.handle("o que é React?") and "Pontos fortes" in engine.handle("o que é React?")
    assert "caso base" in engine.handle("explique recursão") and "LIFO" in engine.handle("o que é uma pilha?")
    assert "O(log n)" in engine.handle("o que é Big-O")


def test_unknown_terms_still_fall_back_to_web_research(engine, monkeypatch):
    from jarvis.local import websearch

    seen = []
    monkeypatch.setattr(websearch, "research", lambda tema, *a, **k: seen.append(tema) or {"fontes": [], "frases": []})
    monkeypatch.setattr(websearch, "format_answer", lambda tema, result: f"web:{tema}")
    assert engine.handle("o que é xadrez").startswith("web:")
    assert engine.handle("como fazer um bolo").startswith("web:") and len(seen) == 2


def test_comparisons_cover_technologies_and_concepts(engine):
    assert "Django × FastAPI" in engine.handle("compare Django e FastAPI") and "Python × Node.js" in engine.handle("Python ou Node?")
    assert "Pilha (stack) × Fila (queue)" in engine.handle("qual a diferença entre pilha e fila")
    assert "Recursão × Laços" in engine.handle("recursão ou laço?")
    assert "Diga os dois itens" in engine.handle("compare isso")


def test_recommendation_and_area_overview(engine):
    assert "Next.js" in engine.handle("qual stack para uma loja virtual?")
    backend = engine.handle("quais linguagens para back end?")
    assert "Back end: o que eu conheço" in backend and "FastAPI" in backend and "Python" in backend and "React" not in backend
    assert "MERN" in engine.handle("qual stack usar?")  # sem tipo de sistema: mostra as stacks que conheço
    assert "Não entendi que tipo de sistema" in engine.handle("que tecnologia usar para isso?")


def test_algorithms_in_the_requested_language(engine):
    java = engine.handle("busca binária em Java")
    assert "```java" in java and "static int buscaBinaria" in java and "não foi compilado aqui" in java
    assert "func fatorial" in engine.handle("escreva um fatorial em Go") and "def ordenar_rapido" in engine.handle("quicksort")
    assert "OrdenarRapido" in engine.handle("quicksort em C#")


def test_logic_method_and_overviews(engine):
    method = engine.handle("como resolver um problema de programação")
    assert "Entenda" in method and "Teste" in method
    assert "Fatorial" in engine.handle("quais algoritmos você sabe") and "Recursão" in engine.handle("quais conceitos você explica")
    assert "Ordenação por bolha" in engine.handle("me ajuda a resolver ordenar uma lista")


# ── criar sistemas ───────────────────────────────────────────────────────

def test_creating_a_system_asks_for_what_is_missing_and_only_proposes(engine, cfg, tmp_path, monkeypatch):
    store = actions.ActionStore(tmp_path / "acoes")
    monkeypatch.setattr(actions, "ActionStore", lambda *a, **k: store)
    assert "Qual o nome" in engine.handle("crie um sistema com FastAPI e React")
    assert "Em qual pasta" in engine.handle("crie um sistema chamado Loja Virtual com FastAPI e React")
    assert "não tenho um modelo pronto para \"django\"" in engine.handle("crie um sistema chamado X com django")
    assert store.pending_since(0) == []

    parent = tmp_path / "Projetos"
    parent.mkdir()
    answer = engine.handle(f"crie um sistema chamado Loja Virtual com FastAPI e React em {parent}")
    [action] = store.pending_since(0)
    assert "Preparei a criação" in answer and action.kind == "criar_projeto" and action.params["modelo"] == "fastapi+react"
    assert not (parent / "Loja Virtual").exists()  # só propôs; criar exige o cartão aprovado


def test_full_stack_without_a_stack_uses_the_recommended_default(engine, tmp_path, monkeypatch):
    store = actions.ActionStore(tmp_path / "acoes")
    monkeypatch.setattr(actions, "ActionStore", lambda *a, **k: store)
    parent = tmp_path / "P"
    parent.mkdir()
    engine.handle(f"crie um sistema full stack chamado Gestao em {parent}")
    assert store.pending_since(0)[0].params["modelo"] == "fastapi+react"


# ── ferramentas MCP ──────────────────────────────────────────────────────

def test_mcp_tools_expose_the_knowledge():
    pytest.importorskip("mcp")
    from jarvis.mcp_tools import logica_tools, stack_tools

    assert "Pontos fortes" in stack_tools.consultar_tecnologia("React") and "Não tenho" in stack_tools.consultar_tecnologia("xadrez")
    assert "Next.js" in stack_tools.listar_tecnologias("full stack") and "React × Vue.js" in stack_tools.comparar_tecnologias("React", "Vue")
    assert "Por quê" in stack_tools.recomendar_stack("sistema de gestão") and "fastapi+react" in stack_tools.modelos_de_projeto()
    assert "caso base" in logica_tools.explicar_conceito("recursão") and "Não tenho" in logica_tools.explicar_conceito("xadrez")
    assert "```go" in logica_tools.exemplo_de_algoritmo("fatorial", "Go") and "Não tenho o algoritmo" in logica_tools.exemplo_de_algoritmo("xyz")
    assert "Entenda" in logica_tools.como_resolver_problema() and "Quicksort" in logica_tools.listar_conceitos_e_algoritmos()


def test_mcp_server_registers_every_programming_tool():
    pytest.importorskip("mcp")
    import asyncio

    from jarvis import mcp_server

    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    expected = {"consultar_tecnologia", "listar_tecnologias", "comparar_tecnologias", "recomendar_stack", "modelos_de_projeto",
                "explicar_conceito", "exemplo_de_algoritmo", "como_resolver_problema", "listar_conceitos_e_algoritmos",
                "propor_criar_projeto"}
    assert expected <= names
