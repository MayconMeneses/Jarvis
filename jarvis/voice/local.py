"""Voz local e offline (Piper TTS): baixa o modelo uma vez e fala sem internet.

Voz padrão: pt_BR-faber-medium (masculina, dados CC0, projeto rhasspy/piper-voices).
Alternativas livres do mesmo catálogo (CC0, ~60 MB, mesma arquitetura "medium", portanto mesma velocidade):
`cadu` e `jeff`, escolhidas em `voz_modelo` da configuração; só são baixadas se escolhidas, com SHA-256 conferido.
Não imita nenhuma voz de filme ou ator: o "ar de Jarvis" é só um reverb discreto, opcional.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import threading
from collections.abc import Callable
from pathlib import Path

import numpy as np

from jarvis.config import data_dir

log = logging.getLogger(__name__)

_RAIZ = "https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/"
BASE = _RAIZ + "faber/medium/"
NOME = "pt_BR-faber-medium"
# nome do arquivo -> SHA-256 conferido no download
ARQUIVOS = {
    f"{NOME}.onnx": "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
    f"{NOME}.onnx.json": "7e694de195ae3fc36dd732c445eb04fb49b649854893cb5506b978f0d50a1d6f",
}
# Vozes alternativas (modelo -> (nome do arquivo, {arquivo: sha256})). Licença CC0 nos três cartões do modelo.
VOZES_ALTERNATIVAS = {
    "cadu": ("pt_BR-cadu-medium", {
        "pt_BR-cadu-medium.onnx": "765f0809a6ea9035d4a6d0d008dbf8876e68b2dd32029312672fa8f405bdb535",
        "pt_BR-cadu-medium.onnx.json": "5fe03aa3d4901880554905b12075713cd552598c8a350455a1ec73f8b4e6be19"}),
    "jeff": ("pt_BR-jeff-medium", {
        "pt_BR-jeff-medium.onnx": "3a6f4c46355813c2b7bbc4d16b6d13d60ed72074b952a393baace82a7d0c94b5",
        "pt_BR-jeff-medium.onnx.json": "7bf8145b572b36806f5ce0f1d3322b6711975bc7d0473e8d36fced4a9ec0030d"}),
}
Progresso = Callable[[str], None]
SILENCIO_ENTRE_TRECHOS_MS = 140


def definicao(modelo: str | None = None) -> tuple[str, str, dict[str, str]]:
    """(nome-base, URL da pasta, {arquivo: sha}) do modelo; desconhecido cai na voz padrão."""
    if modelo in VOZES_ALTERNATIVAS:
        nome, arquivos = VOZES_ALTERNATIVAS[modelo]
        return nome, f"{_RAIZ}{modelo}/medium/", arquivos
    return NOME, BASE, ARQUIVOS


def threads_padrao() -> int:
    """Núcleos físicos aproximados (metade dos lógicos), de 1 a 4: mais que isso só briga com a janela e o microfone."""
    return max(1, min(4, (os.cpu_count() or 2) // 2))


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


def voz_instalada(pasta: Path | None = None, modelo: str | None = None) -> bool:
    """True se o modelo e a configuração já estão na pasta (confere só o tamanho, que é barato)."""
    pasta = pasta or pasta_vozes()
    return all((pasta / nome).exists() and (pasta / nome).stat().st_size > 0 for nome in definicao(modelo)[2])


def pasta_embutida() -> Path:
    """Onde o instalador deixa a voz (<app>/modelos/vozes; em packaging/modelos/vozes no código-fonte)."""
    from jarvis.voice.models import bundled_root

    return bundled_root() / "vozes"


def baixar_voz(on_status: Progresso | None = None, pasta: Path | None = None, baixar=None, embutida: Path | None = None,
               modelo: str | None = None) -> Path:
    """Usa a voz embutida no instalador ou baixa uma vez (60 MB) para %LOCALAPPDATA%/SuperJarvis/vozes e confere o SHA-256. Reaproveita o que já está lá."""
    from jarvis.llm.baixar import baixar_arquivo

    baixar = baixar or baixar_arquivo
    pasta = pasta or pasta_vozes()
    dito = on_status or (lambda _: None)
    _, base, arquivos = definicao(modelo)
    for nome, sha in arquivos.items():
        destino = pasta / nome
        if _confere(destino, sha):
            continue
        embutido = (embutida or pasta_embutida()) / nome  # veio dentro do instalador: copia, sem internet
        if _confere(embutido, sha):
            pasta.mkdir(parents=True, exist_ok=True)
            shutil.copy2(embutido, destino)
            continue
        dito(f"Baixando a voz local da Jarvis ({nome})…")
        baixar(base + nome, destino, on_status)
        if _sha256(destino) != sha:
            destino.unlink(missing_ok=True)
            raise RuntimeError(f"{nome} veio corrompido (SHA-256 não confere); tente de novo")
    dito("Voz local instalada.")
    return pasta


def com_reverb_discreto(pcm: np.ndarray, taxa: int) -> np.ndarray:
    """Dois ecos curtos e fracos (sala pequena) para um timbre mais 'de painel'.

    O áudio ganha uma cauda de 60 ms para o último eco não ser cortado no meio (o fade-out final cuida do resto).
    """
    x = pcm.astype(np.float32)
    cauda = int(taxa * 0.06)
    saida = np.concatenate([x, np.zeros(cauda, dtype=np.float32)])
    for ms, ganho in ((23, 0.14), (47, 0.07)):
        n = int(taxa * ms / 1000)
        saida[n:n + x.size] += ganho * x
    pico = float(np.abs(saida).max())
    if pico > 32000:
        saida *= 32000 / pico
    return saida.astype(np.int16)


class PiperVoice:
    """Mesma interface da EdgeVoice: synthesize(texto) -> np.int16 mono, em `sample_rate`."""

    sample_rate = 22050

    def __init__(self, efeito: bool = True, pasta: Path | None = None, modelo: str | None = None, threads: int = 0) -> None:
        self.efeito = efeito
        self.pasta = pasta
        self.modelo = modelo or "faber"
        self.threads = threads or threads_padrao()
        self._voz = None
        self._trava = threading.Lock()

    def _sessao(self, onnx: str, config: str):
        """Piper com a sessão do onnxruntime ajustada (threads fixas, execução sequencial). Se a API mudar, usa o padrão do Piper."""
        from piper import PiperVoice as Piper

        try:
            import inspect
            import json

            import onnxruntime
            from piper.config import PiperConfig

            opcoes = onnxruntime.SessionOptions()
            opcoes.intra_op_num_threads = self.threads
            opcoes.inter_op_num_threads = 1
            opcoes.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
            opcoes.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
            espeak = inspect.signature(Piper.load).parameters["espeak_data_dir"].default
            dados = json.loads(Path(config).read_text(encoding="utf-8"))
            return Piper(config=PiperConfig.from_dict(dados), espeak_data_dir=Path(espeak), download_dir=Path.cwd(),
                         session=onnxruntime.InferenceSession(onnx, sess_options=opcoes, providers=["CPUExecutionProvider"]))
        except (ImportError, AttributeError, KeyError, TypeError) as exc:
            log.info("ajuste de threads indisponível (%s); usando a sessão padrão do Piper", exc)
            return Piper.load(onnx, config_path=config)

    def _arquivos_corrompidos(self) -> bool:
        """Confere o SHA-256 só quando o carregamento falha; arquivo ruim é apagado para ser baixado de novo."""
        pasta = self.pasta or pasta_vozes()
        ruim = False
        for nome, sha in definicao(self.modelo)[2].items():
            if not _confere(pasta / nome, sha):
                (pasta / nome).unlink(missing_ok=True)
                ruim = True
        return ruim

    def _carregar(self):
        with self._trava:
            if self._voz is None:
                pasta = self.pasta or pasta_vozes()
                nome = definicao(self.modelo)[0]
                if not voz_instalada(self.pasta, self.modelo):
                    raise RuntimeError("a voz local ainda não foi baixada")
                base = str(pasta / nome)
                try:
                    self._voz = self._sessao(base + ".onnx", base + ".onnx.json")
                except Exception as exc:  # noqa: BLE001 - onnxruntime: arquivo truncado, protobuf inválido...
                    if self._arquivos_corrompidos():
                        raise RuntimeError("o modelo da voz local estava corrompido; será baixado de novo") from exc
                    raise
                self.sample_rate = self._voz.config.sample_rate
        return self._voz

    def aquecer(self) -> None:
        """Carrega o modelo e faz uma síntese curta: a 1ª chamada é a mais lenta e não deve ser a de uma resposta."""
        self.synthesize("Olá.")

    def synthesize(self, text: str) -> np.ndarray:
        voz = self._carregar()
        pausa = np.zeros(int(self.sample_rate * SILENCIO_ENTRE_TRECHOS_MS / 1000), dtype=np.int16)
        partes: list[np.ndarray] = []
        for trecho in voz.synthesize(text):
            if partes:
                partes.append(pausa)  # a Piper 1.x não coloca silêncio entre as sentenças de uma mesma chamada
            partes.append(trecho.audio_int16_array)
        if not partes:
            raise RuntimeError("a voz local não gerou áudio")
        pcm = np.concatenate(partes).astype(np.int16)
        return com_reverb_discreto(pcm, self.sample_rate) if self.efeito else pcm
