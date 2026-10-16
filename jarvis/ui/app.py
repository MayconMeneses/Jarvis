"""Janela de chat (pywebview) + ícone na bandeja.

Fechar a janela só a esconde; para encerrar, use "Sair" no ícone da bandeja.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import time
from pathlib import Path

import webview

from jarvis import briefing, config, files, memory_db
from jarvis.brains import NoBrainAvailable
from jarvis.chat import Conversation
from jarvis.config import Config
from jarvis.pc import actions
from jarvis.ui import tray

log = logging.getLogger(__name__)
HTML = Path(__file__).with_name("chat.html")


class Api:
    """Métodos chamados pelo JavaScript da janela (window.pywebview.api.*).

    Atributos com "_" não são expostos ao JavaScript.
    """

    def __init__(
        self, cfg: Config, conversation: Conversation, store: actions.ActionStore | None = None
    ) -> None:
        self._cfg = cfg
        self._conversation = conversation
        self._store = store or actions.ActionStore()
        self._voice = None  # VoiceLoop, quando a voz está ativa
        self._memory = memory_db.open_memory(cfg)
        self._files = files.AttachmentStore()
        self._window = None  # definida em run(); usada no seletor de arquivos

    def _diary(self, entry: str) -> None:
        try:
            self._memory.diary(entry)
        except (sqlite3.Error, OSError):
            log.warning("não foi possível escrever no diário", exc_info=True)

    def greeting(self) -> str:
        """Saudação + clima (+ manchetes na 1ª abertura do dia), também falada."""
        try:
            result = briefing.build(config.load())
        except Exception:
            log.exception("falha no briefing")
            return f"Olá, {self._cfg.user_name}! Como você está?"
        self._conversation.remember_said(result["text"])
        if self._voice is not None:
            threading.Thread(target=self._voice.speak, args=(result["speak"],), daemon=True).start()
        return result["text"]

    def open_link(self, url: str) -> bool:
        """Abre no navegador padrão. Só http(s): nada de file:, javascript: etc."""
        url = str(url)
        if not url.startswith(("https://", "http://")):
            return False
        import webbrowser

        return webbrowser.open(url)

    def system_stats(self) -> dict:
        """Números reais para os medidores do HUD (leitura leve, sem esperar)."""
        import psutil

        disk = psutil.disk_usage("C:\\")
        return {
            # Cada chamada vem de uma thread nova: interval=None sempre daria 0 na 1ª leitura.
            "cpu": round(psutil.cpu_percent(interval=0.3)),
            "ram": round(psutil.virtual_memory().percent),
            "disco": round(disk.percent),
        }

    def voice_available(self) -> bool:
        return self._voice is not None

    def listen_now(self) -> None:
        if self._voice is not None:
            self._voice.listen_now()

    # ── anexos ───────────────────────────────────────────────────────────
    def pick_files(self) -> dict:
        """Abre o seletor de arquivos do Windows e guarda cópias dos escolhidos."""
        dialog = getattr(getattr(webview, "FileDialog", None), "OPEN", None) or webview.OPEN_DIALOG
        chosen = self._window.create_file_dialog(dialog, allow_multiple=True) if self._window else None
        return self._store_many([("path", p) for p in (chosen or [])])

    def attach_data(self, name: str, b64: str) -> dict:
        """Arquivo arrastado para a janela (o navegador entrega o conteúdo, não o caminho)."""
        import base64

        try:
            data = base64.b64decode(str(b64), validate=True)
        except ValueError:
            return {"anexos": [], "erros": [f"{name}: conteúdo inválido"]}
        return self._store_many([("data", (str(name), data))])

    def _store_many(self, items) -> dict:
        added, errors = [], []
        for kind, value in items:
            try:
                att = self._files.add_path(value) if kind == "path" else self._files.add(*value)
                added.append(att.public())
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        return {"anexos": added, "erros": errors}

    def send(self, text: str, attachments: list | None = None) -> dict:
        started = time.time()
        text = str(text)
        if attachments:
            listed = []
            for att_id in attachments:
                try:
                    att = self._files.get(str(att_id))
                    listed.append(f"- {att.nome} ({att.tipo}, {att.tamanho_kb} KB) — id {att.id}")
                except ValueError as exc:
                    listed.append(f"- anexo {att_id}: {exc}")
            text = (text or "Analise os arquivos anexados.") + (
                "\n\n[Arquivos anexados pelo usuário — leia com ler_anexo(id):]\n" + "\n".join(listed))
        self._diary(f"Pedido: {text[:300]}")
        try:
            answer = self._conversation.ask(text)
        except NoBrainAvailable as exc:
            return {"error": str(exc)}
        except Exception:  # a janela nunca deve travar por um erro inesperado
            log.exception("erro ao responder")
            return {"error": "Erro inesperado. Detalhes no log da Jarvis."}
        proposals = [
            {"id": a.id, "descricao": a.descricao, "motivo": a.motivo}
            for a in self._store.pending_since(started)
        ]
        return {"text": answer.text, "brain": answer.brain, "actions": proposals,
                "qualidade": self._evaluate(text, answer, time.time() - started)}

    def _evaluate(self, question: str, answer, seconds: float) -> dict | None:
        """Critérios de qualidade de toda resposta (heurísticas leves, sem modelo) + registro."""
        from jarvis.eval import quality

        try:
            result = quality.evaluate(question, answer.text)
        except Exception:
            log.debug("avaliação da resposta falhou", exc_info=True)
            return None
        try:
            from jarvis.config import data_dir

            record = {"quando": time.time(), "cerebro": answer.brain, "segundos": round(seconds, 2),
                      "media": result["media"], "notas": result["notas"], "pergunta": question[:200]}
            with (data_dir() / "avaliacoes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return result

    def decide(self, action_id: str, approve: bool) -> dict:
        try:
            action = actions.decide(self._store, str(action_id), bool(approve))
        except (ValueError, FileNotFoundError) as exc:
            return {"status": "falhou", "resultado": str(exc)}
        log.info("ação %s %s: %s", action.kind, action.status, action.resultado)
        self._diary(f"Ação {action.status}: {action.descricao} {action.resultado}")
        self._conversation.note(f"Ação '{action.descricao}' {action.status}. {action.resultado}")
        return {"status": action.status, "resultado": action.resultado}

    def review_run(self, run_id: str, keep: bool) -> dict:
        """Manter ou desfazer as mudanças que o Claude Code fez num projeto."""
        from jarvis.dev import runs

        try:
            run = runs.review(runs.RunStore(), str(run_id), bool(keep))
        except (ValueError, RuntimeError, OSError) as exc:
            return {"status": "falhou", "resultado": str(exc)}
        message = run.alteracoes.splitlines()[-1]
        self._diary(f"Mudanças no projeto {run.projeto}: {run.revisao}. {message}")
        self._conversation.note(f"Mudanças do Claude Code no projeto {run.projeto}: {run.revisao} "
                                f"pelo usuário. {message}")
        return {"status": run.revisao, "resultado": message}

    # ── cérebros (Claude, Gemini, NVIDIA) ─────────────────────────────────
    def brains_status(self) -> dict:
        from jarvis import environment, keys

        cfg = config.load()
        return {
            "claude": bool(environment.find_claude(cfg.claude.executable)),
            "gemini": bool(keys.get_key("gemini")),
            "nvidia": bool(keys.get_key("nvidia")),
            "brave": bool(keys.get_key("brave")),
            "uso_gemini": cfg.uso_gemini,
            "somente_independente": cfg.somente_independente,
            "modelo_gemini": cfg.gemini.model,
        }

    def environment_notices(self) -> list[str]:
        """Avisos de coisas externas que faltam (Claude Code, git), mostrados ao abrir a janela."""
        from jarvis import environment, keys

        cfg = config.load()
        return environment.notices(cfg, has_other_brain=bool(keys.get_key("gemini") or keys.get_key("nvidia")))

    def save_key(self, provider: str, key: str) -> dict:
        """Testa a chave com uma pergunta mínima e só guarda se funcionar (nunca devolve a chave)."""
        from jarvis import keys
        from jarvis.brains.base import BrainUnavailable
        from jarvis.brains.openai_compat import OpenAICompat

        provider = str(provider)
        key = "".join(str(key).split())  # tira espaços e quebras de linha coladas junto
        if provider not in keys.ENV_NAMES:
            return {"ok": False, "mensagem": "provedor inválido"}
        if len(key) < 20:
            return {"ok": False, "mensagem": "isso não parece uma chave de API (muito curta)"}
        log.info("testando chave do %s (%d caracteres, início %s…)", provider, len(key), key[:4])
        if provider == "brave":  # buscador (não é IA): testa uma busca
            from jarvis.local import websearch

            try:
                websearch.brave("teste", key, limit=1)
            except Exception as exc:
                log.info("chave do brave recusada: %s", exc)
                return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
            keys.set_key("brave", key)
            return {"ok": True, "mensagem": "Chave do Brave testada e guardada: busca completa na web sem IA ativada."}
        try:
            cfg = config.load()
            provider_cfg = getattr(cfg, provider)
            brain = OpenAICompat(provider, provider_cfg, lambda _name: key)
            test = [{"role": "user", "content": "Responda apenas: ok"}]
            try:
                brain.ask(test, "Teste de conexão.")
            except BrainUnavailable as exc:
                log.info("teste do %s com o modelo %s: %s", provider, provider_cfg.model, exc)
                if not str(exc).startswith("modelo não encontrado"):
                    return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
                # A chave foi aceita, mas o nome do modelo não existe mais: escolhe um disponível.
                provider_cfg.model = pick_model(brain.list_models(), provider)
                log.info("modelo do %s trocado para %s", provider, provider_cfg.model)
                brain.ask(test, "Teste de conexão.")
                config.save(cfg)
            keys.set_key(provider, key)
        except (BrainUnavailable, ValueError) as exc:
            log.info("chave do %s recusada: %s", provider, exc)
            return {"ok": False, "mensagem": f"A chave não funcionou: {exc}"}
        except Exception as exc:  # nunca deixa o botão preso sem resposta
            log.exception("erro inesperado ao salvar a chave do %s", provider)
            return {"ok": False, "mensagem": f"Erro inesperado ao salvar: {exc}"}
        log.info("chave do %s guardada (modelo %s)", provider, provider_cfg.model)
        return {"ok": True, "mensagem": f"Chave do {provider.capitalize()} testada e guardada no cofre do "
                                        f"Windows (modelo {provider_cfg.model})."}

    def remove_key(self, provider: str) -> dict:
        from jarvis import keys

        if str(provider) in keys.ENV_NAMES:
            keys.delete_key(str(provider))
        return {"ok": True}

    def set_gemini_mode(self, mode: str) -> dict:
        from jarvis.brains import policy

        if mode not in policy.MODES:
            return {"ok": False}
        cfg = config.load()
        cfg.uso_gemini = mode
        config.save(cfg)
        return {"ok": True}

    def set_standalone(self, on: bool) -> dict:
        """Liga/desliga o modo "sem nenhuma IA". Vale no próximo pedido (o roteador relê a configuração)."""
        cfg = config.load()
        cfg.somente_independente = bool(on)
        config.save(cfg)
        if on:
            self._diary("Modo sem IA ligado")
            return {"ok": True, "mensagem": "Ligado: só a inteligência da Jarvis responde a partir de agora."}
        self._diary("Modo sem IA desligado")
        return {"ok": True, "mensagem": "Desligado: o Claude, o Gemini e a NVIDIA voltam a ajudar."}

    def reset(self) -> None:
        self._conversation.reset()

    # ── visualizador da memória (janela "Memória") ──────────────────────
    def memory_list(self, query: str = "") -> dict:
        """Notas mais recentes ou o resultado de uma busca."""
        try:
            if str(query).strip():
                notes = [{"ref": h["nota"], "resumo": h["trecho"]} for h in self._memory.search(str(query), 40)]
            else:
                notes = [{"ref": n["ref"], "resumo": n["resumo"], "atualizado": n["atualizado"][:10]}
                         for n in self._memory.list_notes(limit=200)]
            return {"notas": notes, "total": self._memory.count()}
        except sqlite3.Error as exc:
            return {"error": f"Não foi possível ler a memória: {exc}"}

    def memory_get(self, ref: str) -> dict:
        try:
            return {"ref": str(ref), "texto": self._memory.read(str(ref), 200_000)}
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}

    def memory_save(self, ref: str, text: str) -> dict:
        try:
            self._memory.edit(str(ref), str(text))
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        self._diary(f"Memória editada na janela: {ref}")
        return {"ok": True}

    def memory_delete(self, ref: str) -> dict:
        try:
            ok = self._memory.delete(str(ref))
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        self._diary(f"Memória apagada na janela: {ref}")
        return {"ok": ok}

    def memory_export(self) -> dict:
        """Grava uma cópia em Markdown numa pasta escolhida (por exemplo, a Jarvis/ de um cofre do Obsidian)."""
        if self._window is None:
            return {"error": "janela indisponível"}
        chosen = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not chosen:
            return {"cancelado": True}
        try:
            count = memory_db.export_markdown(self._memory, chosen[0])
        except (OSError, sqlite3.Error) as exc:
            return {"error": f"Não foi possível exportar: {exc}"}
        return {"text": f"{count} nota(s) gravadas em {chosen[0]}."}

    def dashboard(self) -> dict:
        """Botão 📊: escolhe um documento e abre o dashboard dele no navegador."""
        from jarvis import dashboard

        if self._window is None:
            return {"error": "janela indisponível"}
        tipos = ("Dados (" + ";".join("*" + e for e in dashboard.SUPPORTED) + ")", "Todos os arquivos (*.*)")
        escolha = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=tipos)
        if not escolha:
            return {"cancelado": True}
        try:
            path = dashboard.build(escolha[0])
        except (ValueError, OSError) as exc:
            return {"error": f"Não foi possível criar o dashboard: {exc}"}
        dashboard.open_in_browser(path)
        self._diary(f"Dashboard criado de {Path(escolha[0]).name}")
        self._conversation.note(f"Criei um dashboard do arquivo {escolha[0]} e abri no navegador ({path}).")
        return {"text": f"📊 Abri no navegador o dashboard de {Path(escolha[0]).name}. "
                        f"Ele fica salvo em {path}."}


def pick_model(models: list[str], provider: str) -> str:
    """Modelo de texto rápido mais recente da lista (Gemini: "flash"; outros: o 1º de chat)."""
    import re

    skip = ("lite", "image", "tts", "audio", "live", "embedding", "vision", "thinking", "exp")
    if provider == "gemini":
        candidates = [m for m in models if "gemini" in m and "flash" in m and not any(s in m for s in skip)]
        if candidates:
            def version(name: str) -> tuple:
                found = re.search(r"(\d+(?:\.\d+)?)", name)
                return (float(found.group(1)) if found else 0.0, "preview" not in name, name)
            return max(candidates, key=version)
    chat = [m for m in models if not any(s in m for s in skip)]
    if not chat:
        raise ValueError("nenhum modelo de texto disponível para esta chave")
    return chat[0]


def build_voice(cfg: Config, api: Api, window):
    from jarvis.voice.loop import VoiceLoop
    from jarvis.voice.stt import Transcriber, vocabulary_hint
    from jarvis.voice.tts import Speaker

    def notify(payload: dict) -> None:
        try:
            window.evaluate_js(f"window.onVoice({json.dumps(payload, ensure_ascii=False)})")
        except Exception:  # janela fechando
            log.debug("não foi possível atualizar a janela", exc_info=True)

    return VoiceLoop(
        respond=api.send,
        notify=notify,
        speaker=Speaker(cfg.voz.voz),
        transcriber=Transcriber(
            cfg.voz.modelo_transcricao, vocabulary_hint(cfg.user_name, cfg.city, cfg.projetos),
            on_status=lambda text: notify({"status": text}),
        ),
        sensitivity=cfg.voz.sensibilidade,
        speak_answers=cfg.voz.falar_respostas,
    )


def build_task_worker(cfg: Config, api: Api, window):
    from jarvis.dev import runs

    def notify(run) -> None:
        label = runs.LABELS[run.modo]
        ok = run.status == "concluida"
        mark, state = ("✅", "concluída") if ok else ("⚠️", "falhou")
        if run.modo == "pesquisar":
            head = f"{mark} {run.projeto} {state}: {run.tarefa[:80]}"
            body = f"{head}\n({run.alteracoes})\n\n{run.resultado}" if run.alteracoes else f"{head}\n\n{run.resultado}"
        else:
            head = f"{mark} {label} do projeto {run.projeto} {state}"
            body = f"{head}:\n{run.resultado}"
            if run.alteracoes:
                body += f"\n\nArquivos alterados:\n{run.alteracoes}"
        if run.revisao == "pendente":
            review = {"id": run.id, "projeto": run.projeto, "diff": run.diff, "arquivos": run.mudancas}
            try:
                window.evaluate_js(f"window.onVoice({json.dumps({'review': review}, ensure_ascii=False)})")
            except Exception:
                log.debug("janela indisponível para a revisão", exc_info=True)
        api._conversation.note(f"{head}. Pedido: {run.tarefa[:200]}. Resultado: {run.resultado[:2000]}")
        api._diary(f"{head}: {run.tarefa[:120]}")
        try:
            window.evaluate_js(f"window.onVoice({json.dumps({'task': body}, ensure_ascii=False)})")
        except Exception:
            log.debug("janela indisponível para o aviso da tarefa", exc_info=True)
        if api._voice is not None:
            api._voice.speak(f"{head}. Os detalhes estão na janela.")

    return runs.RunWorker(runs.RunStore(), cfg.claude, notify, mem=api._memory)


def window_geometry(width: int = 440, height: int = 720, margin: int = 12) -> tuple[int, int, int, int]:
    """Canto inferior direito da área útil do monitor (sem cobrir a barra de tarefas)."""
    import ctypes
    import ctypes.wintypes as wt

    area = wt.RECT()
    if not ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(area), 0):  # SPI_GETWORKAREA
        return 100, 60, width, min(height, 680)
    usable = area.bottom - area.top - 2 * margin
    height = max(480, min(height, usable))
    return area.right - width - margin, area.bottom - height - margin, width, height


_ERROR_ALREADY_EXISTS = 183


def claim_single_instance(name: str = "Local\\SuperJarvis"):
    """Mutex nomeado do Windows. Retorna o handle, ou None se outra Jarvis já está aberta."""
    import ctypes

    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, False, name)
    if kernel32.GetLastError() == _ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def build_session_watcher(api: Api, window):
    """Avisa quando uma sessão do Claude Code no PC passa a esperar o usuário."""
    from jarvis.dev import sessions

    def notify(session) -> None:
        text = "⏳ " + session.frase()
        api._conversation.note(text)
        try:
            window.evaluate_js(f"window.onVoice({json.dumps({'task': text}, ensure_ascii=False)})")
        except Exception:
            log.debug("janela indisponível para o aviso da sessão", exc_info=True)
        if api._voice is not None:
            talvez = "talvez " if session.motivo.startswith("talvez") else ""
            api._voice.speak(f"A sessão {session.nome}, do projeto {session.projeto}, "
                             f"{talvez}está {sessions.DESCRICAO[session.estado]}.")

    return sessions.SessionWatcher(notify)


def run(cfg: Config, conversation: Conversation) -> int:
    instance = claim_single_instance()
    if instance is None:
        import ctypes

        ctypes.windll.user32.MessageBoxW(
            None, "A Jarvis já está aberta. Procure o ícone dela na bandeja, perto do relógio.", "Jarvis", 0x40
        )
        return 0
    api = Api(cfg, conversation)
    x, y, width, height = window_geometry()
    window = webview.create_window(
        "Jarvis",
        html=HTML.read_text(encoding="utf-8"),
        js_api=api,
        x=x, y=y, width=width, height=height,
        min_size=(360, 480),
        background_color="#04070C",
    )
    api._window = window
    quitting = False
    voice = build_voice(cfg, api, window) if cfg.voz.ativa else None
    api._voice = voice
    tasks = build_task_worker(cfg, api, window)
    watcher = build_session_watcher(api, window)

    def on_closing() -> bool:
        if quitting:
            return True
        window.hide()
        return False  # cancela o fechamento: a Jarvis continua na bandeja

    def quit_app() -> None:
        nonlocal quitting
        quitting = True
        if voice is not None:
            voice.stop()
        tasks.stop()
        watcher.stop()
        conversation.router.stop()  # fecha a sessão do Claude
        icon.stop()
        window.destroy()

    def talk_now() -> None:
        window.show()
        api.listen_now()

    icon = tray.create(on_open=window.show, on_quit=quit_app, voice=voice, on_talk=talk_now)
    window.events.closing += on_closing

    def on_started() -> None:
        # Abre a sessão do Claude já na largada: a 1ª pergunta não paga a inicialização.
        threading.Thread(target=conversation.warm_up, daemon=True, name="jarvis-aquecer").start()
        icon.run_detached()
        tasks.start()
        watcher.start()
        if voice is not None:
            voice.start()

    webview.start(on_started)
    return 0
