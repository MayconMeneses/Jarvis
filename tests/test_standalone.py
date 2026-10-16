"""Jarvis sem nenhuma IA: modo "somente independente" e as habilidades do motor próprio."""

import pytest

from jarvis import brains, memory_db
from jarvis.config import Config
from jarvis.local.engine import LocalEngine

MSG = [{"role": "user", "content": "me ajuda a planejar a semana"}]


@pytest.fixture
def cfg(tmp_path):
    return Config(memoria_db=str(tmp_path / "m.db"), user_name="Maycon")


@pytest.fixture
def engine(cfg):
    return LocalEngine(load_config=lambda: cfg, brave_key=lambda: None)


def say(engine, text):
    return engine.handle(text)


# ── modo somente independente ────────────────────────────────────────────

def test_standalone_mode_never_calls_any_ai_and_switches_without_restart(monkeypatch, tmp_path):
    monkeypatch.setattr(brains, "write_mcp_config", lambda path=None: tmp_path / "m.json")
    current = Config(memoria_db=str(tmp_path / "m.db"))
    monkeypatch.setattr("jarvis.config.load", lambda: current)
    monkeypatch.setattr(brains.time if hasattr(brains, "time") else __import__("time"), "monotonic", lambda: 10**9)
    router = brains.build_router(current)

    def names():
        router_now = [b.name for b in router.order(MSG)]
        return router_now

    assert names() == ["claude", "gemini", "nvidia", "local"]
    current.somente_independente = True
    # o roteador relê a configuração a cada pedido (cache de 1 s): avança o relógio do teste
    import time as time_module

    monkeypatch.setattr(time_module, "monotonic", lambda: 2 * 10**9)
    assert names() == ["local"]
    current.somente_independente = False
    monkeypatch.setattr(time_module, "monotonic", lambda: 3 * 10**9)
    assert names() == ["claude", "gemini", "nvidia", "local"]


def test_standalone_mode_does_not_warm_up_claude(monkeypatch, tmp_path):
    from jarvis.brains.router import Router

    class Brain:
        def __init__(self, name):
            self.name, self.warmed = name, False

        def warm_up(self, system):
            self.warmed = True

    claude, local = Brain("claude"), Brain("local")
    Router([claude, local], visible=lambda b: b is local).warm_up("sistema")
    assert (claude.warmed, local.warmed) == (False, True)


# ── memória por comando ──────────────────────────────────────────────────

def test_remember_and_recall_by_voice_without_ai(engine, cfg):
    answer = say(engine, "Jarvis, lembre que eu prefiro vagas remotas de back-end")
    assert "Anotado" in answer and "◈ Memória" in answer
    mem = memory_db.open_memory(cfg)
    assert mem.index_text().startswith("- Eu prefiro vagas remotas de")
    assert "vagas remotas" in say(engine, "o que você sabe sobre vagas remotas?")
    assert "vagas remotas" in say(engine, "o que você sabe sobre mim")
    assert "Não achei nada" in say(engine, "o que você lembra sobre xadrez")
    assert "Ainda não guardei" in LocalEngine(load_config=lambda: Config(memoria_db=cfg.memoria_db + "2"),
                                              brave_key=lambda: None).handle("o que você sabe sobre mim")


def test_search_my_memory_is_not_a_web_search(engine, monkeypatch):
    from jarvis.local import websearch

    monkeypatch.setattr(websearch, "research", lambda *a, **k: pytest.fail("não deve ir para a internet"))
    say(engine, "anota que o aniversário da Ana é em março")
    assert "aniversário" in say(engine, "busque na minha memória sobre aniversário")


# ── perfil e projetos ────────────────────────────────────────────────────

def test_profile_fields_by_voice(engine, cfg, monkeypatch):
    from jarvis import config as config_module
    from jarvis.info import jobs

    monkeypatch.setattr(config_module, "save", lambda c, path=None: None)
    assert "Nível = Pleno" in say(engine, "meu nível é Pleno")
    assert "Stack = Python e React" in say(engine, "minha stack é Python e React.")
    assert "Evitar = PHP" in say(engine, "quero evitar PHP")
    assert "Cidade = Croatá" in say(engine, "minha cidade é Croatá") and cfg.city == "Croatá"
    profile, _ = jobs.load_profile(memory_db.open_memory(cfg))
    assert profile["nivel"] == "pleno" and profile["stack"] == ["Python e React"] and profile["evitar"] == ["PHP"]
    assert "Diga, por exemplo" not in say(engine, "meu nível é sênior")


def test_projects_and_cards_by_voice(engine, cfg, tmp_path):
    folder = tmp_path / "Loja"
    folder.mkdir()
    assert "Nenhum projeto" in say(engine, "meus projetos")
    cfg.projetos["Loja Virtual"] = str(folder)
    assert "Loja Virtual" in say(engine, "quais são os meus projetos")
    assert "Anotado na ficha do projeto loja virtual" in say(engine, "anota no projeto loja virtual que decidimos usar Postgres")
    assert "Postgres" in say(engine, "ficha do projeto Loja Virtual")
    assert "ainda não tem ficha" in say(engine, "ficha do projeto Sem Nada").lower() or "não cadastrado" in say(engine, "ficha do projeto Sem Nada")


# ── dashboard e sessões ──────────────────────────────────────────────────

def test_dashboard_command_builds_and_opens(engine, tmp_path, monkeypatch):
    from jarvis import dashboard

    doc = tmp_path / "Vendas 2026.csv"
    doc.write_text("mes;total\njan;10\n", encoding="utf-8")
    opened = []
    monkeypatch.setattr(dashboard, "data_dir", lambda: tmp_path)
    monkeypatch.setattr(dashboard, "open_in_browser", opened.append)
    answer = say(engine, f'Crie um dashboard de "{doc}"')
    assert "Vendas 2026.csv" in answer and len(opened) == 1 and opened[0].parent == tmp_path / "dashboards"
    assert "Diga o arquivo" in say(engine, "cria um dashboard de ")  # sem arquivo: pergunta


def test_sessions_question_is_answered_locally(engine, monkeypatch):
    from jarvis.dev import sessions

    waiting = sessions.Session("s1", "Loja", "C:\\x", "Teste", "permissao", "permission prompt")
    monkeypatch.setattr(sessions.SessionReader, "sessions", lambda self: [waiting])
    assert "Teste" in say(engine, "alguma sessão do Claude Code está me esperando?")
    monkeypatch.setattr(sessions.SessionReader, "sessions", lambda self: [])
    assert "Nenhuma sessão" in say(engine, "tem sessão do claude code esperando")


def test_new_commands_do_not_steal_existing_ones(engine):
    assert engine.classify("abre o WhatsApp")[0] == "abrir"
    assert engine.classify("pesquise sobre Docker")[0] == "pesquisa"
    assert engine.classify("quero vagas remotas")[0] == "vagas"
    assert engine.classify("lembre que prefiro vagas remotas")[0] == "lembrar"
    assert engine.classify("como está o pc")[0] == "pc"
    assert engine.is_direct_command("meu nível é pleno") and not engine.is_direct_command("lembre que gosto de café")


def test_window_toggle_saves_the_standalone_flag(tmp_path, monkeypatch):
    pytest.importorskip("webview")
    from jarvis import config
    from jarvis.ui.app import Api

    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "detect_obsidian_vault", lambda *a: "")
    api = Api(Config(memoria_db=str(tmp_path / "m.db")), conversation=None)
    assert config.load().somente_independente is False
    assert "só a inteligência da Jarvis" in api.set_standalone(True)["mensagem"]
    assert config.load().somente_independente is True and api.brains_status()["somente_independente"] is True
    assert "voltam a ajudar" in api.set_standalone(False)["mensagem"]
    assert config.load().somente_independente is False
