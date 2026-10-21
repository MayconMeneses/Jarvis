"""Tarefas em segundo plano da janela: voz, fila do Claude Code e monitor de sessões.

Cada fábrica devolve um objeto com start()/stop() e avisa a janela por push().
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from jarvis.config import Config

if TYPE_CHECKING:  # evita importar a API (e o pywebview) só para tipar
    from jarvis.ui.api import Api

log = logging.getLogger(__name__)


def push(window, payload: dict) -> None:
    """Envia um evento para a janela (window.onVoice). Ignora se a janela já fechou."""
    try:
        window.evaluate_js(f"window.onVoice({json.dumps(payload, ensure_ascii=False)})")
    except Exception:
        log.debug("janela indisponível", exc_info=True)


def enviar_visual(window, payload: dict) -> None:
    """Dado para o orbe ({"tipo": "fala"|"fim"|"mic", ...}) pelo mesmo window.onVoice; o JS distingue pelo "tipo"."""
    push(window, payload)


def build_voice(cfg: Config, api: Api, window):
    from jarvis.voice.loop import VoiceLoop
    from jarvis.voice.stt import Transcriber, vocabulary_hint
    from jarvis.voice.tts import Speaker

    speaker = Speaker(cfg.voz.voz, cfg.voz.voz_motor, cfg.voz.voz_efeito,
                      on_visual=lambda payload: enviar_visual(window, payload), atraso_ms=cfg.voz.atraso_visual_ms,
                      modelo_local=cfg.voz.voz_modelo, threads=cfg.voz.voz_threads)
    speaker.preparar(lambda text: push(window, {"status": text}))
    return VoiceLoop(
        respond=api.send,
        notify=lambda payload: push(window, payload),
        speaker=speaker,
        transcriber=Transcriber(
            cfg.voz.modelo_transcricao, vocabulary_hint(cfg.user_name, cfg.city, cfg.projetos),
            on_status=lambda text: push(window, {"status": text}),
        ),
        sensitivity=cfg.voz.sensibilidade,
        speak_answers=cfg.voz.falar_respostas,
    )


def _task_texts(run, labels: dict) -> tuple[str, str]:
    """(título, corpo) do aviso de uma tarefa que terminou."""
    mark, state = ("✅", "concluída") if run.status == "concluida" else ("⚠️", "falhou")
    if run.modo == "pesquisar":
        head = f"{mark} {run.projeto} {state}: {run.tarefa[:80]}"
        extra = f"\n({run.alteracoes})" if run.alteracoes else ""
        return head, f"{head}{extra}\n\n{run.resultado}"
    head = f"{mark} {labels[run.modo]} do projeto {run.projeto} {state}"
    body = f"{head}:\n{run.resultado}"
    if run.alteracoes:
        body += f"\n\nArquivos alterados:\n{run.alteracoes}"
    return head, body


def build_task_worker(cfg: Config, api: Api, window):
    from jarvis.dev import runs

    def notify(run) -> None:
        head, body = _task_texts(run, runs.LABELS)
        if run.revisao == "pendente":
            review = {"id": run.id, "projeto": run.projeto, "diff": run.diff, "arquivos": run.mudancas,
                      "propria": run.projeto == "Super Jarvis"}
            push(window, {"review": review})
        api._conversation.note(f"{head}. Pedido: {run.tarefa[:200]}. Resultado: {run.resultado[:2000]}")
        api._diary(f"{head}: {run.tarefa[:120]}")
        push(window, {"task": body})
        if api._voice is not None:
            api._voice.speak(f"{head}. Os detalhes estão na janela.")

    return runs.RunWorker(runs.RunStore(), cfg.claude, notify, mem=api._memory)


def novos_avisos_de_uso(mem, intervalo: float = 300.0):
    """Avisos de uso de IA ainda não entregues, conferidos no máximo a cada 5 min (a coleta lê arquivos)."""
    import time

    from jarvis.uso import alertas

    ultimo = {"em": 0.0, "lista": []}

    def conferir() -> list:
        if time.monotonic() - ultimo["em"] >= intervalo:
            ultimo["em"] = time.monotonic()
            ultimo["lista"] = alertas.verificar()
        return [(k, t) for k, t in ultimo["lista"] if not mem.meta("proativo:" + k)]

    return conferir


def build_proactive(cfg: Config, api: Api, window):
    """Iniciativa própria: avisos sem ser chamada (ver jarvis/proativo)."""
    import psutil

    from jarvis import briefing, config
    from jarvis.dev import habilidades
    from jarvis.proativo import projetos_sem_commit
    from jarvis.proativo.agendador import Agendador

    def entregar(aviso, falar: bool) -> None:
        api._conversation.note(aviso.texto)
        api._diary("Aviso da Jarvis: " + aviso.texto[:120])
        push(window, {"aviso": aviso.texto})
        if falar and aviso.falar and api._voice is not None:
            api._voice.speak(aviso.falar)

    return Agendador(config.load, api._memory, entregar, lambda: round(psutil.virtual_memory().percent),
                     briefing=lambda: briefing.build(config.load()), treino=habilidades.treino_da_semana,
                     projetos_parados=projetos_sem_commit, uso=novos_avisos_de_uso(api._memory))


def build_autonomo(cfg: Config, api: Api, window):
    """Aprendizado autônomo (ver jarvis/autonomo): estuda sozinha o que mais conversamos, com o PC parado."""
    from jarvis import config, keys
    from jarvis.autonomo.agendador import Autonomo
    from jarvis.dev import conhecimento, saber
    from jarvis.local import websearch

    def entregar(texto: str) -> None:
        api._conversation.note(texto)
        api._diary("Aprendizado autônomo: " + texto[:120])
        push(window, {"aviso": texto})

    def cita(texto: str) -> list[dict]:
        return [i for _, i in saber.citados(texto)] + list(conhecimento.mentioned(texto))

    def avaliar_semana() -> str:
        from jarvis.local import llm_skills

        return llm_skills.avaliar("", config.load()) if config.load().llm_local else "Avaliação semanal do cérebro local: o cérebro local está desligado."

    return Autonomo(config.load, api._memory, entregar, websearch.research, websearch.format_answer, cita,
                    ultimo_pedido=lambda: api._ultimo_pedido, chave_brave=lambda: keys.get_key("brave"), avaliar_semana=avaliar_semana)


def build_session_watcher(api: Api, window):
    """Avisa quando uma sessão do Claude Code no PC passa a esperar o usuário."""
    from jarvis.dev import sessions

    def notify(session) -> None:
        text = "⏳ " + session.frase()
        api._conversation.note(text)
        push(window, {"task": text})
        if api._voice is not None:
            talvez = "talvez " if session.motivo.startswith("talvez") else ""
            api._voice.speak(f"A sessão {session.nome}, do projeto {session.projeto}, "
                             f"{talvez}está {sessions.DESCRICAO[session.estado]}.")

    return sessions.SessionWatcher(notify)
