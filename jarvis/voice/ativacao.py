"""Ativação por "Jarvis" + comando na mesma frase, e o estado do microfone mostrado na janela.

Lógica pura (sem microfone, sem janela), testável com áudio sintético. Tudo fica na memória:
nenhum áudio é gravado em disco e nenhum sai do PC.
"""

from __future__ import annotations

import re
import time
import unicodedata
from collections import deque
from collections.abc import Callable
from difflib import SequenceMatcher

import numpy as np

from jarvis.voice.gravador import FRAME
from jarvis.voice.stt import SAMPLE_RATE

# Estados do microfone (window.onVoice {"escuta": estado}).
DESLIGADO, AGUARDANDO, OUVINDO, PROCESSANDO, FALANDO = "desligado", "aguardando", "ouvindo", "processando", "falando"
ESTADOS = (DESLIGADO, AGUARDANDO, OUVINDO, PROCESSANDO, FALANDO)


def estado_base(pausada: bool, ligado: bool = True) -> str:
    """Estado quando nada está acontecendo: desligado (pausada ou sem voz) ou aguardando a palavra de ativação."""
    return AGUARDANDO if ligado and not pausada else DESLIGADO


class FocoEscuta:
    """Ao entrar no modo foco liga a escuta; ao sair devolve o estado em que o usuário a deixou."""

    def __init__(self, auto: bool = True) -> None:
        self.auto = auto
        self._antes: bool | None = None  # "pausada" antes do foco; None = fora do foco

    @property
    def ativo(self) -> bool:
        return self._antes is not None

    def entrar(self, pausada: bool) -> bool:
        """Devolve o valor de "pausada" que deve valer dentro do foco."""
        if self._antes is None:
            self._antes = pausada
        return False if self.auto else pausada

    def sair(self) -> bool | None:
        """"pausada" a restaurar, ou None se não estava no foco."""
        antes, self._antes = self._antes, None
        return antes


# ── palavra de ativação lida na transcrição ──────────────────────────────
_ANTES = {"hey", "hei", "ei", "eia", "ey", "oi", "ola", "opa", "ok", "okay", "o", "e", "ai", "fala", "fale", "veja"}
_MENCAO = {"e", "eh", "foi", "era", "seria", "tambem"}  # "o Jarvis é um filme": falar DO Jarvis, não COM ele
_NAO = {"travis", "jarbas", "marvin", "harvey"}
_INICIAIS = "jgdcy"
# Como o Whisper costuma ouvir um "Jarvis" falado em português (medido com voz sintética): só vale no começo da frase.
_OUVIDO_ERRADO = {"avos", "aves", "javis", "arvis", "jarvi"}


def _sem_acento(txt: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", txt.lower()) if unicodedata.category(c) != "Mn")


def _e_jarvis(token: str) -> bool:
    if token in _OUVIDO_ERRADO:
        return True
    return (token not in _NAO and token[:1] in _INICIAIS
            and SequenceMatcher(None, token, "jarvis").ratio() >= 0.8)


def extrair_comando(texto: str) -> str | None:
    """None = a frase não chama a Jarvis. "" = só a chamou. Senão, o comando que veio depois do nome.

    O nome precisa estar no começo da frase (até 2 palavras antes, como "hey" ou "e aí"): citar a Jarvis no meio
    de uma conversa ou de um vídeo não ativa nada.
    """
    achados = [(m.group(), m.end()) for m in re.finditer(r"\w+", texto)]
    palavras = [(_sem_acento(p), fim) for p, fim in achados]
    for i, (p, fim) in enumerate(palavras[:3]):
        if _e_jarvis(p):
            resto = texto[fim:]
            seguinte = palavras[i + 1][0] if i + 1 < len(palavras) else ""
            if seguinte in _MENCAO and not re.match(r"\s*[,.:;!?\-–—]", resto):
                return None
            return resto.lstrip(" ,.:;!?-–—…\t\n").strip()
        if p not in _ANTES:
            return None
    return None


# ── "Jarvis, ..." sem o modelo de palavra de ativação: pedaços de fala por energia ──
class Segmentador:
    """Junta os quadros de uma frase (do início da voz até uma pausa) e a entrega pronta para transcrever."""

    def __init__(self, ruido: float, silencio_s: float = 0.7, max_s: float = 10.0, min_s: float = 0.4,
                 pre_frames: int = 3) -> None:
        self.limiar = max(ruido * 3.0, 400.0)
        self._silencio = int(silencio_s * SAMPLE_RATE / FRAME)
        self._max = int(max_s * SAMPLE_RATE / FRAME)
        self._min = int(min_s * SAMPLE_RATE / FRAME)
        self._pre: deque[np.ndarray] = deque(maxlen=pre_frames)
        self._frames: list[np.ndarray] = []
        self._mudo = 0

    @property
    def falando(self) -> bool:
        return bool(self._frames)

    def reiniciar(self) -> None:
        self._pre.clear()
        self._frames = []
        self._mudo = 0

    def feed(self, frame: np.ndarray, energia: float) -> np.ndarray | None:
        """Áudio float32 da frase quando ela termina (e é longa o bastante); senão None."""
        alto = energia > self.limiar
        if not self._frames:
            if not alto:
                self._pre.append(frame)
                return None
            self._frames = [*self._pre, frame]
            self._pre.clear()
            self._mudo = 0
            return None
        self._frames.append(frame)
        self._mudo = 0 if alto else self._mudo + 1
        if self._mudo < self._silencio and len(self._frames) < self._max:
            return None
        util = len(self._frames) - self._mudo
        audio = np.concatenate(self._frames).astype(np.float32) / 32768.0 if util >= self._min else None
        self.reiniciar()
        return audio


class LimitadorTranscricao:
    """No máximo `n` transcrições por `janela_s`: protege o PC fraco de falar sem parar ao fundo (TV, reunião)."""

    def __init__(self, n: int = 10, janela_s: float = 60.0, relogio: Callable[[], float] = time.monotonic) -> None:
        self.n, self.janela_s, self._relogio = n, janela_s, relogio
        self._marcas: deque[float] = deque()

    def permite(self) -> bool:
        agora = self._relogio()
        while self._marcas and agora - self._marcas[0] > self.janela_s:
            self._marcas.popleft()
        if len(self._marcas) >= self.n:
            return False
        self._marcas.append(agora)
        return True
