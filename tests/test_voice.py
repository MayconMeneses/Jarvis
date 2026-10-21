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
    assert clean_for_speech(text) == "rám: noventa e cinco por cento. item. código na janela. veja link npm"


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


def test_sentences_are_split_and_short_ones_merged():
    from jarvis.voice.tts import split_sentences

    parts = split_sentences("Oi. Tudo bem? A RAM está em 94%, o que é bastante alto para este PC. Quer que eu veja?")
    assert parts == ["Oi. Tudo bem? A RAM está em 94%, o que é bastante alto para este PC.", "Quer que eu veja?"]
    assert split_sentences("") == []


def test_speaker_plays_first_sentence_without_waiting_for_the_rest(monkeypatch):
    import threading
    import time
    from jarvis.voice import tts

    from sd_falso import sd_falso

    played, release = [], threading.Event()

    class SlowEdge:
        sample_rate = 24000

        def synthesize(self, text):
            if text.startswith("Segunda"):
                release.wait(2)  # a 2ª frase demora para sintetizar
            return np.full(2400, 3000, dtype=np.int16)

    fake_sd, registro = sd_falso()
    monkeypatch.setitem(__import__("sys").modules, "sounddevice", fake_sd)
    speaker = tts.Speaker(motor="online")
    speaker.edge = SlowEdge()
    t = threading.Thread(target=speaker.say, args=("Primeira frase bem longa para não ser juntada. Segunda frase também longa o bastante.",))
    t.start()
    time.sleep(0.4)
    assert len(registro.fluxos) == 1 and registro.fluxos[0].escritos  # a 1ª já tocou
    assert sum(b.size for b in registro.fluxos[0].escritos) < 10000  # só a 1ª parte (2400 + pausa de 220 ms); a 2ª ainda não
    release.set()
    t.join(3)
    assert sum(b.size for b in registro.fluxos[0].escritos) >= 14000


def types_module(**attrs):
    import types

    return types.SimpleNamespace(**attrs)


def test_whisper_hallucinations_are_dropped():
    from jarvis.voice.stt import is_hallucination

    assert is_hallucination("Legendas pela comunidade Amara.org", 3.0)
    assert is_hallucination("Obrigado.", 0.8)
    assert not is_hallucination("Obrigado.", 3.0)  # fala real mais longa
    assert not is_hallucination("Quanto de RAM estou usando?", 2.0)


def test_vocabulary_includes_user_city_and_projects():
    from jarvis.voice.stt import vocabulary_hint

    hint = vocabulary_hint("Maycon", "Fortaleza, Ceará", ["MeuApp", "MeuSistema"])
    assert hint.startswith("Maycon, Fortaleza, MeuApp, MeuSistema, Jarvis")


def test_chime_is_heard_before_recording_and_its_audio_is_discarded():
    loop, events, speaker = make_loop("oi")
    chimes = []
    speaker.chime = lambda: chimes.append(loop._frames.qsize())
    for f in silence(5):  # áudio do próprio bipe, que deve ser descartado
        loop._frames.put(f)

    def feed_after_chime():
        import time
        time.sleep(0.2)
        for f in speech(5) + silence(30):
            loop._frames.put(f)
    import threading
    threading.Thread(target=feed_after_chime).start()
    loop._handle_turn()
    assert chimes == [5] and speaker.said == ["Resposta para: oi"]


def test_pause_toggle_notifies_window():
    loop, events, _ = make_loop("x")
    loop.set_paused(True)
    assert loop.paused.is_set() and events[-1] == {"status": "Escuta pausada"}
    loop.set_paused(False)
    assert not loop.paused.is_set()
