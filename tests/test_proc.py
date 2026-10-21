"""jarvis/proc.py: processos nascem sem janela de console, e nada no app cria processo por fora dele."""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from jarvis import proc

RAIZ = Path(__file__).resolve().parent.parent / "jarvis"
CHAMADAS_PROIBIDAS = {"run", "Popen", "call", "check_call", "check_output", "getoutput", "getstatusoutput"}
# Exceções explícitas: arquivo -> (por que pode). Hoje só o helper; os.startfile abre o protocolo ms-settings: pelo shell (sem console).
LISTA_BRANCA = {
    "proc.py": "é o helper central",
    "pc/launcher.py": "os.startfile('ms-settings:') delega ao shell do Windows, sem console",
}


class FalsoPopen:
    chamadas: list = []

    def __init__(self, args, **opcoes):
        FalsoPopen.chamadas.append(opcoes)


@pytest.fixture
def falso(monkeypatch):
    FalsoPopen.chamadas = []
    monkeypatch.setattr(subprocess, "Popen", FalsoPopen)
    return FalsoPopen


def test_no_windows_abrir_oculta_console_e_janela(falso, monkeypatch):
    monkeypatch.setattr(proc, "_windows", lambda: True)
    monkeypatch.setattr(subprocess, "STARTUPINFO", lambda: type("SI", (), {"dwFlags": 0, "wShowWindow": 5})(), raising=False)
    proc.abrir(["git", "log"], cwd="x")
    opcoes = falso.chamadas[0]
    assert opcoes["creationflags"] & proc.CREATE_NO_WINDOW
    assert opcoes["startupinfo"].dwFlags & 1 and opcoes["startupinfo"].wShowWindow == 0
    assert opcoes["cwd"] == "x"


def test_abrir_visivel_nao_esconde_a_janela_do_programa(falso, monkeypatch):
    monkeypatch.setattr(proc, "_windows", lambda: True)
    proc.abrir_visivel(["explorer.exe"])
    opcoes = falso.chamadas[0]
    assert opcoes["creationflags"] & proc.CREATE_NO_WINDOW and "startupinfo" not in opcoes


@pytest.mark.parametrize("flag", [proc.DETACHED_PROCESS, proc.CREATE_NEW_CONSOLE])
def test_flags_explicitas_de_console_sao_respeitadas(falso, monkeypatch, flag):
    monkeypatch.setattr(proc, "_windows", lambda: True)
    proc.abrir_visivel(["x"], creationflags=flag)
    assert falso.chamadas[0]["creationflags"] == flag


def test_fora_do_windows_nada_muda(falso, monkeypatch):
    monkeypatch.setattr(proc, "_windows", lambda: False)
    proc.abrir(["ls"], cwd="y", creationflags=0)
    assert falso.chamadas[0] == {"cwd": "y", "creationflags": 0}


def test_executar_repassa_timeout_texto_e_captura(monkeypatch):
    vistos = {}

    def falso_run(*args, **opcoes):
        vistos.update(opcoes)
        return subprocess.CompletedProcess(args, 0, "ok", "")

    monkeypatch.setattr(proc, "_windows", lambda: True)
    monkeypatch.setattr(subprocess, "run", falso_run)
    monkeypatch.setattr(subprocess, "STARTUPINFO", lambda: type("SI", (), {"dwFlags": 0, "wShowWindow": 5})(), raising=False)
    saida = proc.executar(["git"], capture_output=True, text=True, encoding="utf-8", timeout=5)
    assert saida.stdout == "ok"
    assert vistos["timeout"] == 5 and vistos["text"] and vistos["capture_output"] and vistos["encoding"] == "utf-8"
    assert vistos["creationflags"] & proc.CREATE_NO_WINDOW


@pytest.mark.skipif(sys.platform != "win32", reason="só no Windows")
def test_rede_de_seguranca_cobre_codigo_de_terceiros(monkeypatch):
    original = subprocess.Popen.__init__
    monkeypatch.setattr(proc, "_ja_ocultou", False)
    try:
        proc.ocultar_consoles()
        saida = subprocess.run([sys.executable, "-c", "print(1)"], capture_output=True, text=True)  # noqa: S603
        assert saida.stdout.strip() == "1"
    finally:
        subprocess.Popen.__init__ = original


def _anotacoes(arvore: ast.AST) -> set[int]:
    ids = set()
    for no in ast.walk(arvore):
        for anotacao in (getattr(no, "annotation", None), getattr(no, "returns", None)):
            if anotacao is not None:
                ids.update(id(n) for n in ast.walk(anotacao))
    return ids


def _violacoes(caminho: Path) -> list[str]:
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    anotacoes = _anotacoes(arvore)
    achados = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name) and id(no) not in anotacoes:
            alvo = (no.value.id, no.attr)
            if (alvo[0] == "subprocess" and alvo[1] in CHAMADAS_PROIBIDAS) or (
                    alvo[0] == "os" and (alvo[1] in {"system", "popen", "startfile"} or alvo[1].startswith(("spawn", "exec")))):
                achados.append(f"{caminho.name}:{no.lineno} {alvo[0]}.{alvo[1]}")
            if alvo[0] == "asyncio" and alvo[1].startswith("create_subprocess"):
                achados.append(f"{caminho.name}:{no.lineno} asyncio.{alvo[1]}")
        if isinstance(no, ast.ImportFrom) and no.module == "subprocess":
            achados += [f"{caminho.name}:{no.lineno} from subprocess import {a.name}" for a in no.names if a.name in CHAMADAS_PROIBIDAS]
    return achados


def test_nenhum_codigo_cria_processo_fora_do_helper():
    achados = []
    for caminho in sorted(RAIZ.rglob("*.py")):
        if caminho.relative_to(RAIZ).as_posix() not in LISTA_BRANCA:
            achados += _violacoes(caminho)
    assert not achados, "use jarvis.proc (executar/abrir/abrir_visivel) em vez de chamar subprocess/os direto: " + "; ".join(achados)


def test_detecta_chamada_direta(tmp_path):
    arquivo = tmp_path / "ruim.py"
    arquivo.write_text("import subprocess, os\nsubprocess.run(['git'])\nx = subprocess.Popen\nos.system('dir')\n", encoding="utf-8")
    assert len(_violacoes(arquivo)) == 3
