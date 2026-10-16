"""Lógica de programação: conceitos e a biblioteca de algoritmos, com o código EXECUTADO de verdade."""

import json
import shutil
import subprocess
import sys

import pytest

from jarvis.dev import logica as L

ALGORITMOS = L.algoritmos()
NODE = shutil.which("node")
GO = shutil.which("go")


def test_library_is_complete_and_consistent():
    assert len(ALGORITMOS) >= 15 and len(L.conceitos()) >= 25
    for a in ALGORITMOS:
        assert {"nome", "problema", "complexidade", "ideia", "pseudocodigo", "codigo", "casos", "funcoes"} <= set(a), a["id"]
        assert set(a["codigo"]) == set(L.LINGUAGENS) and set(a["funcoes"]) == set(L.LINGUAGENS), a["id"]
        assert a["casos"] and a["go_teste"] and a["go_saida"] and len(a["ideia"]) >= 3, a["id"]
        for lang, code in a["codigo"].items():
            assert a["funcoes"][lang] in code, (a["id"], lang)  # o nome da função combina com o código
            assert code.count("{") == code.count("}"), (a["id"], lang)
            assert code.count("(") == code.count(")"), (a["id"], lang)


@pytest.mark.parametrize("a", ALGORITMOS, ids=lambda a: a["id"])
def test_python_version_passes_every_case(a):
    namespace: dict = {}
    exec(a["codigo"]["python"], namespace)  # nosec: código da própria biblioteca
    func = namespace[a["funcoes"]["python"]]
    for args, esperado in a["casos"]:
        assert func(*args) == esperado, (a["id"], args)


@pytest.mark.skipif(NODE is None, reason="node não está instalado")
@pytest.mark.parametrize("a", ALGORITMOS, ids=lambda a: a["id"])
def test_javascript_version_passes_every_case(a, tmp_path):
    func = a["funcoes"]["javascript"]
    calls = ", ".join(f"{func}(...{json.dumps(args)})" for args, _ in a["casos"])
    script = tmp_path / "t.js"
    script.write_text(a["codigo"]["javascript"] + f"\nconsole.log(JSON.stringify([{calls}]));\n", encoding="utf-8")
    result = subprocess.run([NODE, str(script)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [esperado for _, esperado in a["casos"]], a["id"]


@pytest.fixture(scope="module")
def go_output(tmp_path_factory):
    """Compila TODOS os algoritmos Go num único programa (um `go run`) e devolve a saída de cada um."""
    if GO is None:
        pytest.skip("go não está instalado")
    folder = tmp_path_factory.mktemp("go")
    (folder / "go.mod").write_text("module algoritmos\n\ngo 1.21\n", encoding="utf-8")
    calls = []
    for a in ALGORITMOS:
        source = f'package main\n\nimport "fmt"\n\n{a["codigo"]["go"]}\n\nfunc teste_{a["id"]}() {{\n\t{a["go_teste"]}\n}}\n'
        (folder / f"{a['id']}.go").write_text(source, encoding="utf-8")
        calls.append(f'\tfmt.Println("== {a["id"]}")\n\tteste_{a["id"]}()')
    (folder / "main.go").write_text('package main\n\nimport "fmt"\n\nfunc main() {\n' + "\n".join(calls) + "\n}\n", encoding="utf-8")
    result = subprocess.run([GO, "run", "."], cwd=folder, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert result.returncode == 0, result.stderr
    outputs, current = {}, None
    for line in result.stdout.splitlines():
        if line.startswith("== "):
            current = line[3:].strip()
            outputs[current] = []
        elif current:
            outputs[current].append(line)
    return {k: "\n".join(v).strip() for k, v in outputs.items()}


@pytest.mark.parametrize("a", ALGORITMOS, ids=lambda a: a["id"])
def test_go_version_prints_the_expected_output(a, go_output):
    assert go_output[a["id"]] == a["go_saida"], a["id"]


# ── consultas ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("texto, esperado", [
    ("como fazer a busca binária", "busca_binaria"), ("busca linear em java", "busca_linear"),
    ("quero ordenar uma lista", "ordenar_bolha"), ("quicksort em go", "ordenar_rapido"), ("o fatorial de 5", "fatorial"),
    ("sequência de fibonacci", "fibonacci"), ("verificar se é primo", "primo"), ("fizz buzz", "fizzbuzz"),
    ("decimal para binário", "binario"), ("contar palavras de um texto", "contar_palavras"),
])
def test_algorithm_lookup_prefers_the_most_specific_name(texto, esperado):
    assert L.algorithm(texto)["id"] == esperado


def test_algorithm_lookup_ignores_unknown_problems():
    assert L.algorithm("calcular o imposto de renda") is None


@pytest.mark.parametrize("texto, esperado", [
    ("em C# e python", "csharp"), ("em js", "javascript"), ("com node", "javascript"), ("golang", "go"), ("em Java", "java"),
    ("busca binaria", "python"),
])
def test_language_detection(texto, esperado):
    assert L.language_in(texto) == esperado


def test_show_includes_idea_pseudocode_and_code_and_flags_untested_languages():
    text = L.show(L.algorithm("busca binária"), "python")
    assert "Ideia" in text and "Pseudocódigo" in text and "```python" in text and "O(log n)" in text
    assert "não foi compilado aqui" not in text
    assert "não foi compilado aqui" in L.show(L.algorithm("fatorial"), "java")
    assert "não foi compilado aqui" in L.show(L.algorithm("fatorial"), "c#")
    assert "Ainda não tenho" in L.show(L.algorithm("fatorial"), "rust")


def test_concepts_are_complete_and_findable():
    for c in L.conceitos():
        assert all(c[k] for k in ("resumo", "passos", "analogia", "exemplo", "erros", "exercicios")), c["id"]
    assert L.concept("a recursão")["id"] == "recursao" and L.concept("Big-O")["id"] == "complexidade"
    assert L.concept("POO")["id"] == "poo" and L.concept("if")["id"] == "condicionais" and L.concept("xadrez") is None
    text = L.describe_concept(L.concept("recursao"))
    assert "caso base" in text and "Analogia" in text and "Erros comuns" in text


def test_method_recognizes_classic_problems_and_admits_the_rest():
    known = L.method("ordenar uma lista em javascript")
    assert "Como resolver" in known and "```javascript" in known and "ordenarBolha" in known
    unknown = L.method("calcular o imposto de renda")
    assert "Não reconheci" in unknown and "Entenda" in unknown
    assert "```" not in L.method("").split("**Exemplo:**")[0] and "Entenda" in L.method("")


def test_overviews_list_everything():
    assert all(a["nome"] in L.algorithms_overview() for a in ALGORITMOS)
    assert all(c["nome"] in L.concepts_overview() for c in L.conceitos())


def test_python_snippets_in_concepts_are_valid_syntax():
    import ast

    for c in L.conceitos():
        example = c["exemplo"]
        if "\n" in example and not example.lstrip().startswith(("SELECT", "GET", "git", "função", "Problema", "rotas", "import time")):
            try:
                ast.parse(example)
            except SyntaxError:
                pytest.fail(f"exemplo de {c['id']} não é Python válido")
