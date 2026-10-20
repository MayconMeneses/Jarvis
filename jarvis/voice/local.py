"""Voz local e offline (Piper TTS): baixa o modelo uma vez e fala sem internet.

Voz padrão: pt_BR-faber-medium (masculina, dados CC0, projeto rhasspy/piper-voices).
Não imita nenhuma voz de filme ou ator: o "ar de Jarvis" é só um reverb discreto, opcional.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from jarvis.config import data_dir

log = logging.getLogger(__name__)

BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/"
NOME = "pt_BR-faber-medium"
# nome do arquivo -> SHA-256 conferido no download
ARQUIVOS = {
    f"{NOME}.onnx": "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
    f"{NOME}.onnx.json": "7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f",
}
Progresso = Callable[[str], None]


def pasta_vozes() -> Path:
    return data_dir() / "vozes"


def _sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while bloco := f.read(1 << 20):
            h.update(bloco)
    return h.hexdigest()


def _confere(caminho: Path, esperado: str) -> bool:
    return caminho.exists() and _sha256(caminho) == esperado


def voz_instalada(pasta: Path | None = None) -> bool:
    """True se o modelo e a configuração já estão na pasta (confere só o tamanho, que é barato)."""
    pasta = pasta or pasta_vozes()
    return all((pasta / nome).exists() and (pasta / nome).stat().st_size > 0 for nome in ARQUIVOS)


def pasta_embutida() -> Path:
    """Onde o instalador deixa a voz (<app>\modelos\vozes; em packaging/modelos/vozes no código-fonte)."""
    from jarvis.voice.models import bundled_root

    return bundled_root() / "vozes"


def baixar_voz(on_status: Progresso | None = None, pasta: Path | None = None, baixar=None, embutida: Path | None = None) -> Path:
    """Usa a voz embutida no instalador ou baixa uma vez (60 MB) para %LOCALAPPDATA%/SuperJarvis/vozes e confere o SHA-256. Reaproveita o que já está lá."""
    from jarvis.llm.baixar import baixar_arquivo

    baixar = baixar or baixar_arquivo
    pasta = pasta or pasta_vozes()
    dito = on_status or (lambda _: None)
    for nome, sha in ARQUIVOS.items():
        destino = pasta / nome
        if _confere(destino, sha):
            continue
        embutido = (embutida or pasta_embutida()) / nome  # veio dentro do instalador: copia, sem internet
        if _confere(embutido, sha):
            pasta.mkdir(parents=True, exist_ok=True)
            shutil.copy2(embutido, destino)
            continue
        dito(f"Baixando a voz local da Jarvis ({nome})…")
        baixar(BASE + nome, destino, on_status)
        if _sha256(destino) != sha:
            destino.unlink(missing_ok=True)
            raise RuntimeError(f"{nome} veio corrompido (SHA-256 não confere); tente de novo")
    dito("Voz local instalada.")
    return pasta


def com_reverb_discreto(pcm: np.ndarray, taxa: int) -> np.ndarray:
    """Dois ecos curtos e fracos (sala pequena) para um timbre mais 'de painel'. Mantém o tamanho."""
    x = pcm.astype(np.float32)
    saida = x.copy()
    for ms, ganho in ((23, 0.14), (47, 0.07)):
        n = int(taxa * ms / 1000)
        saida[n:] += ganho * x[:-n]
    pico = float(np.abs(saida).max())
    if pico > 32000:
        saida *= 32000 / pico
    return saida.astype(np.int16)


class PiperVoice:
    """Mesma interface da EdgeVoice: synthesize(texto) -> np.int16 mono, em `sample_rate`."""

    sample_rate = 22050

    def __init__(self, efeito: bool = True, pasta: Path | None = None) -> None:
        self.efeito = efeito
        self.pasta = pasta
        self._voz = None
        self._trava = threading.Lock()

    def _carregar(self):
        with self._trava:
            if self._voz is None:
                from piper import PiperVoice as Piper

                base = (self.pasta or pasta_vozes()) / NOME
                if not voz_instalada(self.pasta):
                    raise RuntimeError("a voz local ainda não foi baixada")
                self._voz = Piper.load(str(base) + ".onnx", config_path=str(base) + ".onnx.json")
                self.sample_rate = self._voz.config.sample_rate
        return self._voz

    def aquecer(self) -> None:
        """Carrega o modelo e faz uma síntese curta: a 1ª chamada é a mais lenta e não deve ser a de uma resposta."""
        self.synthesize("Olá.")

    def synthesize(self, text: str) -> np.ndarray:
        voz = self._carregar()
        partes = [c.audio_int16_array for c in voz.synthesize(text)]
        if not partes:
            raise RuntimeError("a voz local não gerou áudio")
        pcm = np.concatenate(partes).astype(np.int16)
        return com_reverb_discreto(pcm, self.sample_rate) if self.efeito else pcm
