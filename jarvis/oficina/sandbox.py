"""Executa código num processo isolado: pasta temporária nova, ambiente limpo, tempo, memória e saída limitados.

Python: `python -I` (ignora variáveis de ambiente e a pasta do usuário). JavaScript: `node`. No Windows o processo entra num Job Object
com limite de memória e que mata os filhos junto (se algo ficar preso, não sobra processo órfão).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

TEMPO_PADRAO = 10
MAX_SAIDA = 20_000
MEMORIA_MB = 512
LINGUAGENS = {"python": ".py", "javascript": ".js"}


@dataclass
class Resultado:
    saida: str = ""
    erro: str = ""
    codigo: int | None = None
    segundos: float = 0.0
    estourou_tempo: bool = False
    truncado: bool = False
    aviso: str = ""
    arquivos: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.codigo == 0 and not self.estourou_tempo

    def texto(self) -> str:
        partes = []
        if self.aviso:
            partes.append(f"⚠ {self.aviso}")
        if self.saida:
            partes.append(self.saida.rstrip())
        if self.erro:
            partes.append("— erros —\n" + self.erro.rstrip())
        if self.estourou_tempo:
            partes.append("⏱ Interrompido: passou do tempo limite.")
        partes.append(f"[{'terminou bem' if self.ok else 'falhou'}"
                      + (f", código {self.codigo}" if self.codigo is not None else "") + f", {self.segundos:.1f} s]")
        return "\n".join(partes)


def interpretador(linguagem: str) -> list[str] | None:
    """Comando do interpretador ou None se não houver. O app instalado não traz Python: usa o do PC, se existir."""
    if linguagem == "python":
        if not getattr(sys, "frozen", False):
            return [sys.executable, "-I", "-X", "utf8"]
        achado = shutil.which("python") or shutil.which("python3")
        return [achado, "-I", "-X", "utf8"] if achado else None
    if linguagem == "javascript":
        achado = shutil.which("node")
        return [achado] if achado else None
    return None


def _ambiente_limpo() -> dict[str, str]:
    base = {k: v for k, v in os.environ.items() if k.upper() in ("PATH", "SYSTEMROOT", "TEMP", "TMP", "COMSPEC", "PATHEXT", "WINDIR")}
    base.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1")
    return base


def _limitar_no_windows(proc: subprocess.Popen) -> None:
    """Job Object: memória máxima e, ao fechar, mata o processo e os filhos. Silencioso se algo falhar."""
    if os.name != "nt":
        return
    try:
        import ctypes
        from ctypes import wintypes

        class Basico(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64), ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.c_size_t), ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class Io(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in ("a", "b", "c", "d", "e", "f")]

        class Estendido(ctypes.Structure):
            _fields_ = [("Basic", Basico), ("Io", Io), ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        k32 = ctypes.windll.kernel32
        job = k32.CreateJobObjectW(None, None)
        info = Estendido()
        info.Basic.LimitFlags = 0x2000 | 0x100 | 0x8  # KILL_ON_JOB_CLOSE | PROCESS_MEMORY | ACTIVE_PROCESS
        info.Basic.ActiveProcessLimit = 8
        info.ProcessMemoryLimit = MEMORIA_MB * 1024 * 1024
        k32.SetInformationJobObject(job, 9, ctypes.byref(info), ctypes.sizeof(info))
        k32.AssignProcessToJobObject(job, int(proc._handle))  # noqa: SLF001
        proc._job = job  # noqa: SLF001  (fica vivo até o fim do processo)
    except Exception:  # noqa: BLE001
        pass


def _matar(proc: subprocess.Popen) -> None:
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=10)
        else:
            proc.kill()
    except (OSError, subprocess.TimeoutExpired):
        proc.kill()


def executar(comando: list[str], pasta: Path, tempo: int = TEMPO_PADRAO) -> Resultado:
    inicio = time.monotonic()
    try:
        proc = subprocess.Popen(comando, cwd=pasta, env=_ambiente_limpo(), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as exc:
        return Resultado(erro=f"não consegui iniciar: {exc}", codigo=-1)
    _limitar_no_windows(proc)
    estourou = False
    try:
        saida, erro = proc.communicate(timeout=tempo)
    except subprocess.TimeoutExpired:
        estourou = True
        _matar(proc)
        saida, erro = proc.communicate()
    truncado = len(saida) > MAX_SAIDA or len(erro) > MAX_SAIDA
    return Resultado(saida[:MAX_SAIDA], erro[:MAX_SAIDA], proc.returncode, time.monotonic() - inicio, estourou, truncado,
                     "A saída foi cortada em 20 mil caracteres." if truncado else "")


def escrever(raiz: Path, arquivos: dict[str, str]) -> None:
    """Grava arquivos só dentro de `raiz` (caminhos simples, sem .. nem unidades)."""
    from jarvis.llm.arquivos import caminho_seguro

    for caminho, conteudo in arquivos.items():
        alvo = raiz / caminho_seguro(caminho)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")


def rodar(linguagem: str, arquivos: dict[str, str], principal: str, tempo: int = TEMPO_PADRAO) -> Resultado:
    """Grava os arquivos numa pasta temporária nova e roda `principal`. A pasta é apagada no fim."""
    comando = interpretador(linguagem)
    if comando is None:
        return Resultado(erro=f"não achei o interpretador de {linguagem} neste PC (instale o Python ou o Node.js).", codigo=-1)
    with tempfile.TemporaryDirectory(prefix="jarvis-oficina-") as pasta:
        raiz = Path(pasta)
        escrever(raiz, arquivos)
        r = executar([*comando, principal], raiz, tempo)
        r.arquivos = sorted(arquivos)
        return r


def testar(linguagem: str, arquivos: dict[str, str], tempo: int = 60) -> Resultado:
    """Python: pytest (se existir) ou unittest. JavaScript: `node --test`."""
    comando = interpretador(linguagem)
    if comando is None:
        return Resultado(erro=f"não achei o interpretador de {linguagem} neste PC.", codigo=-1)
    if linguagem == "python":
        import importlib.util

        argumentos = ["-m", "pytest", "-q", "--tb=short", "-p", "no:cacheprovider"] if importlib.util.find_spec("pytest") else ["-m", "unittest", "discover", "-v"]
    else:
        argumentos = ["--test"]
    with tempfile.TemporaryDirectory(prefix="jarvis-oficina-") as pasta:
        raiz = Path(pasta)
        escrever(raiz, arquivos)
        r = executar([*comando, *argumentos], raiz, tempo)
        r.arquivos = sorted(arquivos)
        return r
