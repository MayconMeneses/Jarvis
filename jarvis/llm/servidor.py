"""Liga o llama-server sob demanda, em 127.0.0.1 numa porta livre, e desliga quando fica parado.

O PC tem pouca memória: o modelo só fica carregado enquanto é usado. Se o usuário já roda Ollama/LM Studio,
`llm_endpoint` aponta para ele e nada é iniciado aqui.
"""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time

from jarvis.brains.base import BrainUnavailable
from jarvis.llm import catalogo, cliente

OCIOSO_SEGUNDOS = 300
ESPERA_CARGA = 180


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor:
    def __init__(self, id_modelo: str, endpoint: str = "", ocioso: float = OCIOSO_SEGUNDOS, lancar=subprocess.Popen) -> None:
        self.id_modelo, self.endpoint, self.ocioso, self._lancar = id_modelo, endpoint.strip(), ocioso, lancar
        self._proc = None
        self._url = ""
        self._uso = 0.0
        self._lock = threading.RLock()

    def comando(self, porta: int) -> list[str]:
        motor, modelo = catalogo.caminho_motor(), catalogo.caminho_modelo(self.id_modelo)
        if motor is None or modelo is None:
            raise BrainUnavailable("o cérebro local não está instalado (peça: \"instalar cérebro local\")")
        return [str(motor), "-m", str(modelo), "--host", "127.0.0.1", "--port", str(porta), "-c", "4096",
                "-t", str(max(1, (os.cpu_count() or 2) - 1))]

    def garantir(self) -> str:
        """URL pronta para uso; inicia o servidor se preciso (a primeira carga leva de 10 a 60 segundos)."""
        with self._lock:
            self._uso = time.monotonic()
            if self.endpoint:
                return self.endpoint
            if self._proc is not None and self._proc.poll() is None and self._url:
                return self._url
            porta = porta_livre()
            self._proc = self._lancar(self.comando(porta), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                      creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self._url = f"http://127.0.0.1:{porta}"
            limite = time.monotonic() + ESPERA_CARGA
            while time.monotonic() < limite:
                if self._proc.poll() is not None:
                    self._proc = None
                    raise BrainUnavailable("o servidor do modelo local fechou ao iniciar (memória insuficiente?)")
                if cliente.no_ar(self._url):
                    threading.Thread(target=self._vigiar, daemon=True).start()
                    return self._url
                time.sleep(1)
            self.parar()
            raise BrainUnavailable("o modelo local demorou demais para carregar")

    def _vigiar(self) -> None:
        while True:
            time.sleep(min(30, max(1, self.ocioso / 4)))
            with self._lock:
                if self._proc is None or self._proc.poll() is not None:
                    return
                if time.monotonic() - self._uso > self.ocioso:
                    self.parar()
                    return

    def marcar_uso(self) -> None:
        self._uso = time.monotonic()

    def rodando(self) -> bool:
        return bool(self.endpoint) or (self._proc is not None and self._proc.poll() is None)

    def parar(self) -> None:
        with self._lock:
            proc, self._proc, self._url = self._proc, None, ""
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
