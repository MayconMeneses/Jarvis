"""Liga o llama-server sob demanda, em 127.0.0.1 numa porta livre, e desliga quando fica parado.

O PC tem pouca memória: o modelo só fica carregado enquanto é usado. Se o usuário já roda Ollama/LM Studio,
`llm_endpoint` aponta para ele e nada é iniciado aqui.
"""

from __future__ import annotations

import socket
import subprocess
import threading
import time

from jarvis import proc as processos
from jarvis.agentes import registro as agentes
from jarvis.brains.base import BrainUnavailable
from jarvis.llm import catalogo, cliente, parametros

OCIOSO_SEGUNDOS = 300
ESPERA_CARGA = 180


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Servidor:
    def __init__(self, id_modelo: str, endpoint: str = "", ocioso: float = OCIOSO_SEGUNDOS, lancar=processos.abrir) -> None:
        self.id_modelo, self.endpoint, self.ocioso, self._lancar = id_modelo, endpoint.strip(), ocioso, lancar
        self._proc = None
        self._url = ""
        self._uso = 0.0
        self._lock = threading.RLock()

    def comando(self, porta: int) -> list[str]:
        motor, modelo = catalogo.caminho_motor(), catalogo.caminho_modelo(self.id_modelo)
        if motor is None or modelo is None:
            raise BrainUnavailable("o cérebro local não está instalado (peça: \"instalar cérebro local\")")
        return [str(motor), *parametros.argumentos(porta, str(modelo), catalogo.modelo(self.id_modelo))]

    def garantir(self) -> str:
        """URL pronta para uso; inicia o servidor se preciso (a primeira carga leva de 10 a 60 segundos)."""
        with self._lock:
            self._uso = time.monotonic()
            if self.endpoint:
                return self.endpoint
            if self._proc is not None and self._proc.poll() is None and self._url:
                return self._url
            porta = porta_livre()
            self._proc = self._lancar(self.comando(porta), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._url = f"http://127.0.0.1:{porta}"
            limite = time.monotonic() + ESPERA_CARGA
            while time.monotonic() < limite:
                if self._proc.poll() is not None:
                    self._proc = None
                    agentes.marcar("llm_local", agentes.ERRO, "fechou ao iniciar")
                    raise BrainUnavailable("o servidor do modelo local fechou ao iniciar (memória insuficiente?)")
                if cliente.no_ar(self._url):
                    threading.Thread(target=self._vigiar, daemon=True).start()
                    agentes.marcar("llm_local", agentes.OK, "carregado")
                    threading.Thread(target=self._aquecer, args=(self._url,), daemon=True).start()
                    return self._url
                time.sleep(1)
            self.parar()
            agentes.marcar("llm_local", agentes.ERRO, "demorou para carregar")
            raise BrainUnavailable("o modelo local demorou demais para carregar")

    def _aquecer(self, url: str) -> None:
        """Processa a persona uma vez, já na carga: a 1ª pergunta do usuário reaproveita esse cache e responde mais rápido."""
        try:
            from jarvis.llm import contexto

            cliente.conversar(url, [{"role": "system", "content": contexto.sistema("", "")}, {"role": "user", "content": "oi"}],
                              max_tokens=1, timeout=120)
        except Exception:  # aquecer é só otimização: se falhar, a conversa segue normal
            pass

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
        if proc is not None:
            agentes.marcar("llm_local", agentes.DESLIGADO, "descarregado")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
