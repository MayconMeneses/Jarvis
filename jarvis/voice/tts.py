"""Fala da Jarvis: voz neural online (edge-tts) com reserva offline do Windows (SAPI)."""

from __future__ import annotations

import asyncio
import logging
import queue
import re
import subprocess
import threading

import numpy as np

log = logging.getLogger(__name__)

MAX_SPOKEN = 600  # caracteres; o resto fica só na janela


def clean_for_speech(text: str) -> str:
    """Tira Markdown, código e links, e encurta respostas longas."""
    text = re.sub(r"```.*?```", " (código na janela) ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"[*_#>|]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > MAX_SPOKEN:
        cut = text[:MAX_SPOKEN]
        end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
        text = (cut[: end + 1] if end > 200 else cut) + " Os detalhes estão na janela."
    return text


def split_sentences(text: str, min_chars: int = 40) -> list[str]:
    """Divide em frases, juntando as muito curtas (cada parte é uma chamada de síntese)."""
    pieces = [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text) if p.strip()]
    parts: list[str] = []
    for piece in pieces:
        if parts and len(parts[-1]) < min_chars:
            parts[-1] += " " + piece
        else:
            parts.append(piece)
    return parts


CHIME_RATE = 24000


def chime_wave() -> np.ndarray:
    """Dois tons ascendentes suaves, com entrada e saída sem estalo."""
    def tone(freq: float, seconds: float) -> np.ndarray:
        t = np.arange(int(CHIME_RATE * seconds)) / CHIME_RATE
        envelope = np.sin(np.pi * t / seconds) ** 2
        return 0.18 * envelope * np.sin(2 * np.pi * freq * t)
    return np.concatenate([tone(880, 0.07), tone(1320, 0.08)]).astype(np.float32)


class EdgeVoice:
    """Voz neural da Microsoft via edge-tts (precisa de internet, sem custo)."""

    sample_rate = 24000

    def __init__(self, voice: str = "pt-BR-FranciscaNeural") -> None:
        self.voice = voice

    def synthesize(self, text: str) -> np.ndarray:
        import edge_tts
        import miniaudio

        async def fetch() -> bytes:
            audio = bytearray()
            async for chunk in edge_tts.Communicate(text, self.voice).stream():
                if chunk["type"] == "audio":
                    audio += chunk["data"]
            return bytes(audio)

        mp3 = asyncio.run(fetch())
        if not mp3:
            raise RuntimeError("edge-tts não retornou áudio")
        decoded = miniaudio.decode(
            mp3, output_format=miniaudio.SampleFormat.SIGNED16, nchannels=1, sample_rate=self.sample_rate
        )
        return np.frombuffer(decoded.samples, dtype=np.int16)


# Lê o texto da entrada padrão: o texto nunca é montado dentro do comando.
_SAPI_SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$v = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'pt-BR' } | Select-Object -First 1;"
    "if ($v) { $s.SelectVoice($v.VoiceInfo.Name) };"
    "$s.Speak([Console]::In.ReadToEnd())"
)


def speak_sapi(text: str) -> None:
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", _SAPI_SCRIPT],
        input=text, text=True, encoding="utf-8", timeout=120,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


class Speaker:
    def __init__(self, voice: str = "pt-BR-FranciscaNeural") -> None:
        self.edge = EdgeVoice(voice)

    def say(self, text: str) -> None:
        """Fala frase a frase: a 1ª começa enquanto as próximas ainda são sintetizadas."""
        import sounddevice as sd

        parts = split_sentences(clean_for_speech(text))
        if not parts:
            return
        ready: queue.Queue = queue.Queue()

        def produce() -> None:
            for i, part in enumerate(parts):
                try:
                    ready.put(("pcm", self.edge.synthesize(part)))
                except Exception as exc:  # sem internet ou serviço fora: voz offline no resto
                    log.info("voz online indisponível (%s); usando a voz do Windows", exc)
                    ready.put(("sapi", " ".join(parts[i:])))
                    break
            ready.put(None)

        threading.Thread(target=produce, daemon=True, name="jarvis-sintese").start()
        while (item := ready.get()) is not None:
            kind, data = item
            if kind == "sapi":
                speak_sapi(data)
            else:
                sd.play(data, self.edge.sample_rate)
                sd.wait()

    def chime(self) -> None:
        """Bipe curto (~0,15 s) para avisar que a Jarvis começou a ouvir."""
        import sounddevice as sd

        sd.play(chime_wave(), CHIME_RATE)
        sd.wait()

    def stop(self) -> None:
        import sounddevice as sd

        sd.stop()
