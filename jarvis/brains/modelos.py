"""Leque de modelos de provedores com catálogo que muda (NVIDIA NIM): usa TODOS os de conversa e ignora os encerrados.

O catálogo da NVIDIA mistura modelos de conversa com embeddings, moderação, visão, voz e tradução, e retira modelos de tempos em
tempos. Em vez de depender de um só, a Jarvis guarda o leque inteiro de conversa (`pool`), tenta na ordem (o último que funcionou
primeiro) e marca como "morto" por alguns dias o que responde que foi aposentado (404/410), sem insistir nele.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from jarvis.config import data_dir

PREFERIDOS_NVIDIA = (
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "mistralai/mistral-large-2-instruct",
    "nvidia/llama-3.1-nemotron-51b-instruct",
    "nvidia/nemotron-3-super-120b-a12b",
    "google/gemma-3-12b-it",
    "nv-mistralai/mistral-nemo-12b-instruct",
    "mistralai/mistral-7b-instruct-v0.3",
    "deepseek-ai/deepseek-v4.1-flash",
    "z-ai/glm-5.3-flash",
    "moonshotai/kimi-k2.6",
)
# Pedaços de nome de modelos que NÃO são de conversa de texto: nunca entram no leque.
NAO_E_CONVERSA = ("embed", "guard", "safety", "reward", "parse", "vlm", "vision", "vila", "neva", "nvclip", "riva", "deplot", "fuyu", "kosmos",
                  "retriev", "calibration", "detector", "cosmos", "topic-control", "diffusion", "tts", "audio", "image", "rerank", "translate", "-base")
# Servem para conversa, mas ficam para o fim (raciocinam em voz alta, são de código ou experimentais).
ULTIMO_RECURSO = ("reasoning", "coder", "codegemma", "codellama", "starcoder", "preview", "exp", "thinking", "lite", "live", "omni")
VALIDADE_MORTO = 3 * 86400  # um modelo "encerrado" é revisto depois de 3 dias (o catálogo pode voltar a tê-lo)


def candidatos(modelos: list[str]) -> list[str]:
    """Todos os modelos de conversa, na ordem em que vale tentar: preferidos, "instruct/chat", os demais e, por último, os de último recurso."""
    uteis = [m for m in modelos if not any(p in m.lower() for p in NAO_E_CONVERSA)]
    preferidos = [m for m in PREFERIDOS_NVIDIA if m in uteis]
    resto = [m for m in uteis if m not in preferidos]
    normais = [m for m in resto if not any(p in m.lower() for p in ULTIMO_RECURSO)]
    fim = [m for m in resto if m not in normais]
    normais.sort(key=lambda m: (not any(p in m.lower() for p in ("instruct", "chat", "-it")), m))
    return preferidos + normais + sorted(fim)


class EstadoModelos:
    """O que a Jarvis aprendeu sobre os modelos de cada provedor: o leque, o último que funcionou e os encerrados (com data)."""

    def __init__(self, arquivo: Path | None = None, agora=time.time) -> None:
        self.arquivo = arquivo or data_dir() / "modelos.json"
        self._agora = agora
        self._trava = threading.Lock()

    def _ler(self) -> dict:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _gravar(self, dados: dict) -> None:
        try:
            self.arquivo.parent.mkdir(parents=True, exist_ok=True)
            self.arquivo.write_text(json.dumps(dados, indent=1), encoding="utf-8")
        except OSError:
            pass  # o leque é uma otimização: sem gravar, só perde a memória entre execuções

    def pool(self, provedor: str) -> list[str]:
        return list(self._ler().get(provedor, {}).get("pool", []))

    def definir_pool(self, provedor: str, modelos: list[str]) -> None:
        with self._trava:
            dados = self._ler()
            dados.setdefault(provedor, {})["pool"] = list(modelos)
            self._gravar(dados)

    def bom(self, provedor: str) -> str | None:
        return self._ler().get(provedor, {}).get("bom")

    def marcar_bom(self, provedor: str, modelo: str) -> None:
        with self._trava:
            dados = self._ler()
            if dados.get(provedor, {}).get("bom") != modelo:
                dados.setdefault(provedor, {})["bom"] = modelo
                self._gravar(dados)

    def mortos(self, provedor: str) -> set[str]:
        agora = self._agora()
        return {m for m, quando in self._ler().get(provedor, {}).get("mortos", {}).items() if agora - quando < VALIDADE_MORTO}

    def marcar_morto(self, provedor: str, modelo: str) -> None:
        with self._trava:
            dados = self._ler()
            dados.setdefault(provedor, {}).setdefault("mortos", {})[modelo] = self._agora()
            self._gravar(dados)

    def ordem(self, provedor: str, padrao: str) -> list[str]:
        """A ordem de tentativa: o último que funcionou, o modelo configurado e o resto do leque, sem os encerrados e sem repetir."""
        mortos = self.mortos(provedor)
        vistos: list[str] = []
        for m in [self.bom(provedor), padrao, *self.pool(provedor)]:
            if m and m not in vistos and m not in mortos:
                vistos.append(m)
        return vistos
