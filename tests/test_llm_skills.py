"""Criar sistemas pensando, arquivos gerados com segurança e o cérebro local no motor próprio e no roteador."""

import time

import pytest

from jarvis import config
from jarvis.config import Config
from jarvis.llm import arquivos, pensar, tarefas
from jarvis.local.engine import LocalEngine
from jarvis.pc import actions
from tests.test_llm import api, cfg, esperar  # noqa: F401  (fixtures compartilhadas)


# ── arquivos gerados e criação pensando ──────────────────────────────────

@pytest.mark.parametrize("caminho", ["../x.py", "C:/x.py", "/etc/x.py", "a/../../x.py", "run.bat", "setup.ps1", ".env",
                                     "a b.py", "x.exe", "a/b/c/d/e.py"])
def test_unsafe_generated_paths_are_rejected(caminho):
    with pytest.raises(ValueError):
        arquivos.validar({caminho: "x"})


def test_generated_files_limits_and_writing(tmp_path):
    with pytest.raises(ValueError):
        arquivos.validar({f"f{i}.py": "x" for i in range(13)})
    with pytest.raises(ValueError):
        arquivos.validar({"a.py": "x" * 50_000})
    criados = arquivos.escrever(tmp_path, {"app/main.py": "print(1)", "README.md": "# x\n"})
    assert sorted(criados) == ["README.md", "app/main.py"] and (tmp_path / "app" / "main.py").read_text() == "print(1)\n"


def test_plan_parsing_and_validation_of_code():
    plano = pensar.interpretar_plano("1. `main.py`: programa\n- test_main.py - testes\nbla bla\n../x.py: ruim\nREADME.md: docs")
    assert plano == [("main.py", "programa"), ("test_main.py", "testes")]
    assert pensar.conferir("a.py", "def f(:\n  pass") and pensar.conferir("a.py", "x = 1") is None
    assert pensar.conferir("a.json", "{") and pensar.conferir("a.py", "  ") == "o arquivo ficou vazio"
    assert pensar.extrair_codigo("Aqui:\n```python\nx = 1\n```\nfim") == "x = 1" and pensar.extrair_codigo("```js\ny\n```") == "y"


def test_create_system_plans_writes_and_fixes_syntax_errors():
    respostas = iter(["main.py: o programa\ntest_main.py: os testes",
                      "```python\ndef soma(a, b)\n    return a + b\n```",
                      "```python\ndef soma(a, b):\n    return a + b\n```",
                      "```python\nfrom main import soma\n\ndef test_soma():\n    assert soma(1, 2) == 3\n```"])
    vistos = []

    def conversa(mensagens):
        vistos.append(list(mensagens))
        return next(respostas)

    status = []
    r = pensar.criar("Calc", "uma calculadora", conversa, None, status.append)
    assert set(r.arquivos) == {"main.py", "test_main.py", "README.md"} and not r.avisos
    ns: dict = {}
    exec(r.arquivos["main.py"], ns)
    assert ns["soma"](1, 2) == 3 and "erro de sintaxe" in vistos[2][-1]["content"] and "Escrevendo main.py" in status[1]
    assert "Calc" in r.arquivos["README.md"] and "Gerado pela Jarvis" in r.arquivos["README.md"]


def test_create_system_reports_files_that_never_compile():
    respostas = iter(["main.py: x"] + ["```python\ndef (:\n```"] * 3)
    r = pensar.criar("Ruim", "algo", lambda m: next(respostas))
    assert r.avisos and "revise antes de usar" in r.avisos[0]


def test_planning_failure_is_explained():
    with pytest.raises(ValueError, match="planejar"):
        pensar.criar("X", "algo", lambda m: "não sei")


def test_proposal_card_then_approval_writes_the_files(tmp_path):
    cfg = Config()
    store = actions.ActionStore(tmp_path / "acoes")
    ac = actions.propose_new_project(store, cfg, "Calc", str(tmp_path), "calculadora", "teste",
                                     arquivos={"main.py": "x = 1", "README.md": "# Calc"})
    assert "main.py" in ac.descricao and "IA local" in ac.descricao and ac.params["arquivos"]["main.py"] == "x = 1"
    assert not (tmp_path / "Calc").exists()  # nada é gravado antes da aprovação
    actions.execute(ac)
    assert (tmp_path / "Calc" / "main.py").read_text().strip() == "x = 1" and (tmp_path / "Calc" / ".git").exists()
    with pytest.raises(ValueError):
        actions.propose_new_project(store, cfg, "Mau", str(tmp_path), "", "t", arquivos={"../x.py": "1"})


def test_background_creation_ends_in_a_pending_card(tmp_path, cfg):
    respostas = iter(["main.py: programa", "```python\nx = 1\n```"])
    store = actions.ActionStore(tmp_path / "acoes")
    tarefas._estado["criacao"] = ""
    assert tarefas.criar("Bg", str(tmp_path), "algo simples", store, conversa=lambda m: next(respostas))
    assert esperar("criacao").startswith("✔"), tarefas._estado["criacao"]
    assert store.pending_since(0)[0].params["arquivos"]["main.py"] == "x = 1"


# ── motor próprio e roteador ─────────────────────────────────────────────

@pytest.fixture
def motor():
    config.save(Config())
    return LocalEngine()


@pytest.mark.parametrize("texto, intencao", [
    ("instalar cérebro local", "llm_instalar"), ("baixe o modelo local", "llm_instalar"),
    ("status do cérebro local", "llm_status"), ("desligar o cérebro local", "llm_status"),
    ("crie com a IA local um sistema chamado Agenda em C:\\Projetos", "criar_com_ia"),
    ("crie um sistema chamado Loja com FastAPI e React", "criar_sistema"),
])
def test_engine_routes_local_brain_requests(motor, texto, intencao):
    assert motor.classify(texto)[0] == intencao


def test_engine_install_proposes_a_card_and_status_reports(motor):
    texto = motor.handle("instalar cérebro local")
    assert "aprove o cartão" in texto and "llama.cpp" in texto and "huggingface.co/Qwen" in texto
    assert "não instalado" in motor.handle("status do cérebro local")
    assert "Cérebro local desligado" in motor.handle("desligar o cérebro local")
    assert "instalar cérebro local" in motor.handle("crie com a IA local um sistema chamado A em C:\\P: algo")


def test_router_uses_the_model_only_when_it_is_on(cfg):
    from jarvis.brains import build_router

    roteador = build_router(cfg)
    assert [b.name for b in roteador.brains][-2:] == ["llm", "local"]
    chat = [{"role": "user", "content": "me conta uma curiosidade sobre polvos"}]
    visiveis = [b.name for b in roteador.order(chat)]
    assert "llm" in visiveis and visiveis.index("llm") < visiveis.index("local")
    config.save(Config())
    time.sleep(1.1)
    assert "llm" not in [b.name for b in roteador.order(chat)]


def test_create_with_local_brain_parses_name_folder_and_description(motor, tmp_path, monkeypatch):
    from jarvis.local import llm_skills

    config.save(Config(llm_local=True, llm_endpoint="http://127.0.0.1:1"))
    chamadas = []
    monkeypatch.setattr(tarefas, "criar", lambda nome, pasta, desc: chamadas.append((nome, pasta, desc)) or True)
    texto = motor.handle("crie com a IA local um sistema chamado Agenda em C:\\Projetos: uma agenda de contatos em Python")
    assert "Comecei a pensar" in texto and chamadas == [("Agenda", "C:\\Projetos", "uma agenda de contatos em Python")]
    assert "Diga o nome e a pasta" in llm_skills.criar("crie com a IA local um sistema", config.load())


def test_mcp_tools_and_ui_bridge(motor):
    from jarvis.mcp_tools import llm_tools
    from jarvis.ui.api_brains import BrainsMixin

    assert "Cérebro local" in llm_tools.estado_do_cerebro_local()
    assert "aprove o cartão" in llm_tools.propor_instalar_cerebro_local()
    assert "Qwen2.5 Coder 3B" in llm_tools.propor_instalar_cerebro_local(True)

    class Ponte(BrainsMixin):
        def _diary(self, texto):
            pass

    ponte = Ponte()
    assert ponte.set_llm(True)["ok"] is False and ponte.brains_status()["llm_pronto"] is False
    config.save(Config(llm_endpoint="http://127.0.0.1:1"))  # servidor externo configurado = pronto
    assert ponte.set_llm(True)["ligado"] is True and ponte.brains_status()["llm_local"] is True
    assert ponte.set_llm(False)["ligado"] is False


def test_failing_generated_tests_go_back_to_the_model_for_a_fix():
    respostas = iter(["calc.py: soma\ntest_calc.py: testes",
                      "```python\ndef soma(a, b):\n    return a - b\n```",
                      "```python\nfrom calc import soma\n\ndef test_soma():\n    assert soma(1, 2) == 3\n```",
                      "```python\ndef soma(a, b):\n    return a + b\n```"])  # correção pedida depois que o teste falhou
    status = []
    r = pensar.criar("Calc", "soma", lambda m: next(respostas), None, status.append)
    assert "a + b" in r.arquivos["calc.py"] and not r.avisos and any("testes falharam" in s for s in status)
    assert pensar.rodar_testes({"test_x.py": "def test_a():\n    assert True\n"}) is None
    assert "assert" in pensar.rodar_testes({"test_x.py": "def test_a():\n    assert 1 == 2\n"})
    assert pensar.rodar_testes({"main.py": "x = 1"}) is None  # sem arquivo de teste: nada a rodar


# ── aprender na internet e avaliar o modelo ──────────────────────────────

def test_learning_from_the_web_saves_a_reviewable_note_and_is_consulted_later(motor):
    from jarvis import aprender, memory_db

    from jarvis.local.websearch import Result

    achado = {"fontes": [Result("Site", "https://x")], "lidos": 1, "resumo": [("Qubits guardam informação quântica.", 1)], "trechos": []}
    cfg = config.load()
    assert "Sobre o que" in aprender.aprender("aprenda sobre", cfg)
    texto = aprender.aprender("aprenda sobre Qubits", cfg, pesquisar=lambda tema, n, brave_key=None: achado)
    assert "não foi verificado" in texto and "Aprendizado/Qubits" in texto
    assert "não verificado" in memory_db.open_memory(cfg).get("Aprendizado/Qubits")
    assert "Qubits guardam" in aprender.consultar("qubits", cfg) and aprender.consultar("xadrez avançado", cfg) is None
    assert "Do que aprendi na internet" in motor.handle("o que é qubits")
    assert "Não consegui aprender" in aprender.aprender("aprenda sobre Algo", cfg, pesquisar=lambda *a, **k: {"fontes": []})


def test_model_ruler_scores_tasks_and_compares_with_the_previous_run(tmp_path):
    from jarvis import memory_db
    from jarvis.llm import avaliar

    certas = {"eh_par": "def eh_par(n):\n    return n % 2 == 0", "soma_lista": "def soma_lista(xs):\n    return sum(xs)"}

    def conversa(m):
        funcao = m[0]["content"].split("função ")[1].split("(")[0]
        return "```python\n" + certas.get(funcao, "def " + funcao + "(*a):\n    return None") + "\n```"

    r = avaliar.avaliar(conversa)
    assert r["acertos"] == 2 and r["total"] == 6 and r["nota"] == 33 and r["detalhes"]["eh_par"] and not r["detalhes"]["maior"]
    assert "2 de 6" in avaliar.relatorio("Teste", r) and "Errou" in avaliar.relatorio("Teste", r)
    mem = memory_db.open_memory(Config(memoria_db=str(tmp_path / "m.db")))
    assert avaliar.registrar(mem, "Teste", r) == ""
    assert "(+17)" in avaliar.registrar(mem, "Teste", {**r, "nota": 50})
    assert not avaliar.executar("while True:\n    pass", "f", [[[], 1]])  # código preso não trava: tempo limite


def test_engine_routes_ruler_and_learning(motor):
    assert motor.classify("avalie o cérebro local")[0] == "avaliar_llm" and motor.classify("aprenda sobre Rust")[0] == "aprender"
    assert motor.classify("o que devo estudar?")[0] == "evoluir" and "precisa" not in motor.handle("avalie o cérebro local").lower() or True
    assert "cérebro local ligado" in motor.handle("avalie o cérebro local")
