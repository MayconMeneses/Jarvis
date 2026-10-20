"""Mapa de áreas do Second Brain e o grafo da aba Memória (dados e segurança do desenho)."""

import re
from pathlib import Path

from jarvis import config, memory_areas
from jarvis.chat import Conversation
from jarvis.pc import actions
from jarvis.ui import web
from jarvis.ui.api import Api

WEB = Path(web.__file__).parent


def test_eight_areas_with_fixed_colors():
    cores = {a["id"]: a["cor"] for a in memory_areas.AREAS}
    assert cores == {"metas": "#fbbf24", "trabalho": "#ff5547", "projetos": "#8b7cff", "financas": "#f7931a",
                     "aprendizado": "#2dd4ff", "saude": "#10b981", "relacoes": "#ec4899", "meta": "#8a90a6"}


def test_area_comes_from_the_ref_prefix():
    esperado = {"Metas/Correr": "metas", "Trabalho/Chefe": "trabalho", "Perfil Profissional": "trabalho",
                "Projetos/Jarvis/Sobre": "projetos", "Finanças/Reserva": "financas", "Aprendido/Python": "aprendizado",
                "Pesquisas/2026 X": "aprendizado", "Saúde/Sono": "saude", "Relações/Ana": "relacoes",
                "Memória/Café": "meta", "Qualquer/Coisa": "meta"}
    assert {ref: memory_areas.area_de(ref) for ref in esperado} == esperado


def test_normalize_is_a_closed_list():
    assert memory_areas.normalizar("Relações") == "relacoes" and memory_areas.normalizar(" meta ") == "meta"
    assert memory_areas.normalizar("segredos") is None and memory_areas.normalizar("../x") is None


def test_graph_links_by_wikilink_and_folder_and_degree():
    notas = [{"ref": "Metas/A", "corpo": "veja [[B]]"}, {"ref": "Metas/B", "corpo": ""}, {"ref": "Saúde/C", "corpo": ""},
             {"ref": "Diário/2026-10-20", "corpo": "- ruído"}]
    g = memory_areas.grafo(notas)
    assert [n["ref"] for n in g["nos"]] == ["Metas/A", "Metas/B", "Saúde/C"]  # sem o diário
    assert g["arestas"] == [[0, 1]]
    assert [n["grau"] for n in g["nos"]] == [1, 1, 0]
    assert len(g["areas"]) == 8


def test_graph_caps_nodes():
    g = memory_areas.grafo([{"ref": f"Metas/N{i}", "corpo": ""} for i in range(400)])
    assert len(g["nos"]) == memory_areas.MAX_NOS


def test_bridge_memory_graph(tmp_path):
    api = Api(config.load(), Conversation(None, "s"), actions.ActionStore(tmp_path / "a"))
    api._memory.put("Metas/Correr", "texto", "memoria")
    api._memory.put("Saúde/Sono", "ver [[Correr]]", "memoria")
    g = api.memory_graph()
    assert {n["ref"] for n in g["nos"]} == {"Metas/Correr", "Saúde/Sono"} and g["arestas"]


# ── segurança do desenho: nada de HTML montado com dados ──────────────────

def test_graph_code_never_builds_html_from_data():
    for nome in ("memory-grafo.js", "memory.js"):
        codigo = (WEB / "js" / nome).read_text(encoding="utf-8")
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function", codigo), nome


def test_graph_files_are_in_the_page_and_the_canvas_exists():
    pagina = web.page()
    assert "const MemoriaGrafo" in pagina and 'id="mem-canvas"' in pagina and "#mem-legenda" in pagina
    assert pagina.index("const MemoriaGrafo") < pagina.index("MemoriaGrafo.aoAbrir")  # definido antes do uso
