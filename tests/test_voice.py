import numpy as np

from jarvis.voice.loop import FRAME, Recorder, VoiceLoop
from jarvis.voice.tts import MAX_SPOKEN, clean_for_speech


def silence(n=1):
    return [np.zeros(FRAME, dtype=np.int16) for _ in range(n)]


def speech(n=1):
    t = np.arange(FRAME) / 16000
    tone = (6000 * np.sin(2 * np.pi * 220 * t)).astype(np.int16)
    return [tone.copy() for _ in range(n)]


def feed_all(rec, frames):
    for i, f in enumerate(frames):
        if rec.feed(f):
            return i + 1
    return None


# ── fim da fala ──────────────────────────────────────────────────────────

def test_recording_ends_after_silence_following_speech():
    rec = Recorder(noise_floor=50)
    frames = silence(3) + speech(10) + silence(30)
    stopped_at = feed_all(rec, frames)
    assert stopped_at is not None and stopped_at < len(frames)
    assert rec.speech_started and rec.audio().dtype == np.float32
    assert np.abs(rec.audio()).max() <= 1.0


def test_no_speech_gives_up_and_returns_empty_audio():
    rec = Recorder(noise_floor=50, no_speech_s=1.0)
    assert feed_all(rec, silence(100)) is not None
    assert rec.audio().size == 0


def test_long_speech_is_capped():
    rec = Recorder(noise_floor=50, max_s=2.0)
    assert feed_all(rec, speech(100)) == int(2.0 * 16000 / FRAME)


def test_loud_background_raises_threshold():
    assert Recorder(noise_floor=1000).threshold == 3000
    assert Recorder(noise_floor=10).threshold == 400


# ── texto falado ─────────────────────────────────────────────────────────

def test_clean_for_speech_removes_markdown_code_and_links():
    text = "**RAM:** 95%\n- item\n```py\nx=1\n```\nveja https://exemplo.com `npm`"
    assert clean_for_speech(text) == "RAM: 95% item (código na janela) veja link npm"


def test_long_answers_are_shortened_for_speech():
    long = ("Esta é uma frase de teste. " * 60).strip()
    spoken = clean_for_speech(long)
    assert len(spoken) <= MAX_SPOKEN + 40 and spoken.endswith("Os detalhes estão na janela.")


# ── ciclo completo com peças falsas ──────────────────────────────────────

class FakeTranscriber:
    def __init__(self, text):
        self.text, self.received = text, None

    def warm_up(self):
        pass

    def transcribe(self, audio):
        self.received = audio
        return self.text


class FakeSpeaker:
    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)


def make_loop(text, respond=None):
    events = []
    speaker = FakeSpeaker()
    loop = VoiceLoop(
        respond=respond or (lambda t: {"text": f"Resposta para: {t}", "brain": "claude", "actions": []}),
        notify=events.append,
        speaker=speaker,
        transcriber=FakeTranscriber(text),
    )
    loop._noise = 50
    return loop, events, speaker


def test_turn_transcribes_answers_and_speaks():
    loop, events, speaker = make_loop("que horas são")
    for f in speech(10) + silence(30):
        loop._frames.put(f)
    loop._handle_turn()  # o próprio teste alimenta a fila de áudio
    assert {"user": "que horas são", "status": "Pensando…"} in events
    assert any("answer" in e for e in events)
    assert speaker.said == ["Resposta para: que horas são"]


def test_turn_with_nothing_understood_does_not_call_brain():
    called = []
    loop, events, speaker = make_loop("", respond=lambda t: called.append(t) or {})
    for f in silence(80):
        loop._frames.put(f)
    loop._handle_turn()
    assert called == [] and speaker.said == []
    assert {"status": "Não entendi. Tente de novo."} in events


def test_errors_are_spoken_with_a_short_message():
    loop, _events, speaker = make_loop("oi", respond=lambda t: {"error": "nenhum cérebro respondeu"})
    for f in speech(5) + silence(30):
        loop._frames.put(f)
    loop._handle_turn()
    assert speaker.said == ["Não consegui responder agora."]


def test_pause_toggle_notifies_window():
    loop, events, _ = make_loop("x")
    loop.set_paused(True)
    assert loop.paused.is_set() and events[-1] == {"status": "Escuta pausada"}
    loop.set_paused(False)
    assert not loop.paused.is_set()
