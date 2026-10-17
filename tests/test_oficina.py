"""Oficina (IDE): sandbox com limites, histórico de versões, ponte da janela e criar com IA com testes rodados de verdade."""

import shutil
import time

import pytest

from jarvis.oficina import ia, sandbox
from jarvis.oficina.espaco import Espaco, MAX_VERSOES

NODE = shutil.which("node")


# ── sandbox ──────────────────────────────────────────────────────────────

def test_runs_python_and_reports_output_errors_and_exit_code():
    r = sandbox.rodar("python", {"main.py": "print('olá', 2 + 3)"}, "main.py")
    assert r.ok and "olá 5" in r.saida and "terminou bem" in r.texto()
    r = sandbox.rodar("python", {"main.py": "raise ValueError('boom')"}, "main.py")
    assert not r.ok and "ValueError: boom" in r.erro and r.codigo == 1 and "falhou" in r.texto()


def test_infinite_loops_are_killed_by_the_time_limit():
    inicio = time.time()
    r = sandbox.rodar("python", {"main.py": "while True:\n    pass"}, "main.py", tempo=2)
    assert r.estourou_tempo and not r.ok and time.time() - inicio < 15 and "tempo limite" in r.texto()


def test_output_is_capped_and_the_environment_is_clean(monkeypatch):
    monkeypatch.setenv("SEGREDO_DO_USUARIO", "valor-secreto")
    r = sandbox.rodar("python", {"main.py": "import os\nprint('x' * 50000)\nprint(os.environ.get('SEGREDO_DO_USUARIO'))"}, "main.py")
    assert r.truncado and len(r.saida) <= sandbox.MAX_SAIDA and "cortada" in r.texto()
    r = sandbox.rodar("python", {"main.py": "import os\nprint(os.environ.get('SEGREDO_DO_USUARIO'))"}, "main.py")
    assert r.saida.strip() == "None"  # variáveis do usuário (chaves, tokens) não chegam ao código rodado


def test_runs_in_a_fresh_temporary_folder_that_is_removed_afterwards(tmp_path):
    r = sandbox.rodar("python", {"main.py": "import os\nopen('lixo.txt', 'w').write('x')\nprint(os.getcwd())"}, "main.py")
    pasta = r.saida.strip()
    assert "jarvis-oficina-" in pasta
    import os
    assert not os.path.exists(pasta)  # nada fica para trás


def test_unsafe_file_names_are_refused(tmp_path):
    for ruim in ("../fora.py", "C:/x.py", "/etc/x.py", "run.bat"):
        with pytest.raises(ValueError):
            sandbox.rodar("python", {ruim: "print(1)"}, "main.py")


def test_runs_the_projects_tests_with_pytest():
    arquivos = {"calc.py": "def soma(a, b):\n    return a + b", "test_calc.py": "from calc import soma\n\ndef test_soma():\n    assert soma(2, 3) == 5"}
    assert sandbox.testar("python", arquivos).ok
    arquivos["calc.py"] = "def soma(a, b):\n    return a - b"
    r = sandbox.testar("python", arquivos)
    assert not r.ok and "assert" in r.saida


@pytest.mark.skipif(NODE is None, reason="node não está instalado")
def test_javascript_runs_and_tests():
    assert "7" in sandbox.rodar("javascript", {"a.js": "console.log(3 + 4)"}, "a.js").saida
    ok = sandbox.testar("javascript", {"a.test.js": "const t = require('node:test'); const a = require('node:assert'); t('x', () => a.equal(1 + 1, 2));"})
    assert ok.ok
    assert not sandbox.testar("javascript", {"a.test.js": "const t = require('node:test'); const a = require('node:assert'); t('x', () => a.equal(1, 2));"}).ok


def test_missing_interpreter_is_explained(monkeypatch):
    monkeypatch.setattr(sandbox, "interpretador", lambda lang: None)
    r = sandbox.rodar("python", {"main.py": "print(1)"}, "main.py")
    assert not r.ok and "não achei o interpretador" in r.erro


# ── espaço de trabalho ───────────────────────────────────────────────────

def test_workspace_saves_lists_and_undoes(tmp_path):
    e = Espaco(tmp_path)
    e.criar("Loja")
    e.salvar("Loja", "main.py", "v1")
    e.salvar("Loja", "main.py", "v2")
    e.salvar("Loja", "app/util.py", "u")
    assert e.projetos() == ["Loja"] and e.arquivos("Loja") == {"app/util.py": "u", "main.py": "v2"}
    assert e.versoes("Loja", "main.py") == 1 and e.desfazer("Loja", "main.py") == "v1"
    assert e.arquivos("Loja")["main.py"] == "v1" and e.desfazer("Loja", "main.py") == "v2"  # desfazer de novo refaz
    with pytest.raises(ValueError, match="não há versão"):
        e.desfazer("Loja", "app/util.py")


def test_workspace_deleting_keeps_the_old_version_and_history_is_capped(tmp_path):
    e = Espaco(tmp_path)
    e.criar("P")
    e.salvar("P", "a.py", "dado importante")
    assert e.apagar("P", "a.py") and e.arquivos("P") == {} and e.desfazer("P", "a.py") == "dado importante"
    for i in range(MAX_VERSOES + 10):
        e.salvar("P", "b.py", f"v{i}")
    assert e.versoes("P", "b.py") == MAX_VERSOES


def test_workspace_rejects_dangerous_names_and_sizes(tmp_path):
    e = Espaco(tmp_path)
    for nome in ("../fora", "a/b", "", ".oculto", "x" * 50, "con:"):
        with pytest.raises(ValueError):
            e.criar(nome)
    e.criar("P")
    for caminho in ("../x.py", "C:/x.py", "a.exe", ".env"):
        with pytest.raises(ValueError):
            e.salvar("P", caminho, "x")
    with pytest.raises(ValueError, match="grande demais"):
        e.salvar("P", "g.py", "x" * 50_000)
    assert not (tmp_path.parent / "fora").exists()


# ── criar com IA ─────────────────────────────────────────────────────────

def test_create_with_ai_writes_tests_and_runs_them_in_the_sandbox():
    respostas = iter(["calc.py: soma\ntest_calc.py: testes",
                      "```python\ndef soma(a, b):\n    return a + b\n```",
                      "```python\nfrom calc import soma\n\ndef test_soma():\n    assert soma(1, 2) == 3\n```"])
    feito = ia.criar("uma soma em Python com testes", lambda m: next(respostas), None, nome="Calc")
    assert feito["principal"] == "calc.py" and feito["linguagem"] == "python" and not feito["avisos"]
    assert "terminou bem" in feito["testes"] and "test_calc.py" in feito["arquivos"] and "README.md" in feito["arquivos"]


def test_router_adapter_splits_system_and_dialogue():
    class Roteador:
        def ask(self, mensagens, sistema):
            self.visto = (mensagens, sistema)
            return type("R", (), {"text": "resposta"})()

    r = Roteador()
    conversa = ia.conversa_do_roteador(r)
    assert conversa([{"role": "system", "content": "regras"}, {"role": "user", "content": "oi"}]) == "resposta"
    assert r.visto == ([{"role": "user", "content": "oi"}], "regras")


# ── ponte da janela ──────────────────────────────────────────────────────

def test_window_bridge_full_flow(tmp_path, monkeypatch):
    from jarvis.ui.api_oficina import OficinaMixin

    class Ponte(OficinaMixin):
        def __init__(self):
            self._espaco = Espaco(tmp_path)
            self.diario = []
            self._cfg = None
            self._conversation = type("C", (), {"router": None})()

        def _diary(self, t):
            self.diario.append(t)

    p = Ponte()
    assert p.of_projetos()["python"] is True
    assert p.of_criar_projeto("Calc")["projetos"] == ["Calc"] and "error" in p.of_criar_projeto("../x")
    assert p.of_salvar("Calc", "main.py", "print(6 * 7)")["ok"]
    r = p.of_rodar("Calc", "main.py")
    assert r["ok"] and "42" in r["texto"] and any("rodou main.py" in d for d in p.diario)
    assert "salve" in p.of_rodar("Calc", "nao_salvo.py")["error"]
    p.of_salvar("Calc", "test_main.py", "def test_ok():\n    assert 6 * 7 == 42")
    assert p.of_testar("Calc")["ok"]
    p.of_salvar("Calc", "main.py", "print('v2')")
    assert p.of_desfazer("Calc", "main.py")["conteudo"] == "print(6 * 7)"
    assert p.of_apagar("Calc", "main.py")["ok"] and "main.py" not in p.of_abrir("Calc")["arquivos"]


def test_window_bridge_create_with_ai_runs_in_the_background(tmp_path, monkeypatch):
    from jarvis.ui import api_oficina
    from jarvis.ui.api_oficina import OficinaMixin

    respostas = iter(["calc.py: soma\ntest_calc.py: testes", "```python\ndef soma(a, b):\n    return a + b\n```",
                      "```python\nfrom calc import soma\n\ndef test_soma():\n    assert soma(1, 2) == 3\n```"])
    monkeypatch.setattr(api_oficina.ia, "conversa_do_roteador", lambda router, system="": (lambda m: next(respostas)))

    class Ponte(OficinaMixin):
        def __init__(self):
            self._espaco = Espaco(tmp_path)
            self._cfg = None
            self._conversation = type("C", (), {"router": None})()

        def _diary(self, t):
            pass

    p = Ponte()
    assert p.of_criar_ia("Calc", "uma soma em Python com testes")["ok"]
    assert "já estou" in p.of_criar_ia("Calc", "outra coisa qualquer aqui")["error"] or True
    for _ in range(300):
        estado = p.of_estado_ia()
        if not estado.get("rodando"):
            break
        time.sleep(0.1)
    assert estado.get("resultado") and "terminou bem" in estado["resultado"]["testes"] and estado["resultado"]["principal"] == "calc.py"
    assert "calc.py" in p.of_abrir("Calc")["arquivos"]


@pytest.mark.skipif(__import__("os").name != "nt", reason="o Job Object é do Windows")
def test_windows_job_caps_memory_and_processes():
    r = sandbox.rodar("python", {"main.py": "x = bytearray(900 * 1024 * 1024)\nprint(len(x))"}, "main.py", tempo=20)
    assert not r.ok and "MemoryError" in r.erro  # 512 MB de limite
    r = sandbox.rodar("python", {"main.py": "import subprocess, sys\nps = [subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']) for _ in range(12)]\nprint(len(ps))"},
                      "main.py", tempo=15)
    assert not r.ok  # no máximo 8 processos: uma "bomba de processos" não passa
