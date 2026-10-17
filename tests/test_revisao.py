"""Revisão de código e de diffs: acha problemas conhecidos só nas linhas adicionadas e nunca executa o que foi colado."""

from jarvis.dev import revisao
from jarvis.local.engine import LocalEngine

# Os valores ruins abaixo são montados por partes para o próprio teste não parecer vazar uma chave.
CHAVE = "AKIA" + "ABCDEFGHIJKLMNOP"
DIFF = f"""diff --git a/app/api.py b/app/api.py
--- a/app/api.py
+++ b/app/api.py
@@ -10,3 +10,9 @@ def listar():
     contexto = 1
-    antigo = "removido com eval(x)"
+    resultado = ev{"al"}(pedido)
+    db.execute(f"SELECT * FROM clientes WHERE nome = '{{nome}}'")
+    subprocess.run(cmd, shell=True)
+    try:
+        gravar()
+    except:
+        pass
+    chave = "{CHAVE}"
+    print("depurando")  # TODO limpar
"""


def regras(texto):
    achados, _ = revisao.revisar(texto)
    return {a.regra for a in achados}, achados


def test_diff_review_flags_risky_added_lines_with_file_and_line():
    nomes, achados = regras(DIFF)
    assert {"Execução de código dinâmico", "SQL montado com texto", "Comando de shell montado como texto", "Exceção engolida",
            "Possível segredo no código", "Pendência marcada", "Saída de depuração", "Código alterado sem teste"} <= nomes
    ev = next(a for a in achados if a.regra == "Execução de código dinâmico")
    assert ev.arquivo == "app/api.py" and ev.linha == 11 and ev.gravidade == "alta"  # linha do ARQUIVO NOVO, não do diff
    assert achados[0].gravidade == "alta" and achados[-1].gravidade in ("baixa", "média")  # as mais graves primeiro
    assert all(CHAVE not in a.trecho for a in achados)  # o relatório nunca repete o segredo


def test_removed_lines_are_not_judged():
    nomes, achados = regras(DIFF)
    assert not any("removido" in a.trecho for a in achados)


def test_diff_with_a_test_file_does_not_complain_about_missing_tests_and_clean_code_passes():
    limpo = ("diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1,2 @@\n x = 1\n+y = 2\n"
             "diff --git a/tests/test_a.py b/tests/test_a.py\n--- a/tests/test_a.py\n+++ b/tests/test_a.py\n@@ -1 +1,2 @@\n a = 1\n+assert y == 2\n")
    achados, resumo = revisao.revisar(limpo)
    assert achados == [] and resumo["arquivos"] == ["a.py", "tests/test_a.py"]
    assert "Não achei problemas" in revisao.relatorio(limpo)


def test_loose_code_snippets_and_big_diffs_and_placeholders():
    nomes, _ = regras("def f(x):\n    return ev" + "al(x)\n")
    assert "Execução de código dinâmico" in nomes
    assert "Possível segredo no código" not in regras('API_KEY = "seu_valor_aqui_xxxxxxxxxxxx"')[0]  # exemplo/placeholder não é vazamento
    grande = "--- a/x.py\n+++ b/x.py\n@@ -0,0 +1,450 @@\n" + "\n".join(f"+linha_{i} = {i}" for i in range(450))
    assert any(a.regra.startswith("Diff grande") for a in revisao.revisar(grande)[0])
    assert any("caracteres" in a.regra for a in revisao.revisar("x = '" + "a" * 200 + "'")[0])


def test_engine_reviews_pasted_diffs(tmp_path):
    motor = LocalEngine(load_config=lambda: None)
    texto = "revise este diff\n" + DIFF
    assert motor.classify(texto)[0] == "revisar" and motor.classify("revise o projeto Loja")[0] == "avaliar_projeto"
    resposta = motor.handle(texto)
    assert "Revisão do diff" in resposta and "Execução de código dinâmico" in resposta and "app/api.py:11" in resposta
    assert "Cole o diff" in motor.handle("revise este trecho")


def test_mcp_tool():
    from jarvis.mcp_tools import engenharia_tools

    assert "Revisão" in engenharia_tools.revisar_codigo("x = 1\n")
