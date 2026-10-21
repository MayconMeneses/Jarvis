import io
import json
from contextlib import contextmanager

import pytest

from jarvis.brains.base import Answer, BrainUnavailable
from jarvis.brains.router import Router
from jarvis.config import Config
from jarvis.local import engine as engine_mod
from jarvis.local import websearch
from jarvis.local.engine import LocalEngine


@pytest.fixture
def local():
    return LocalEngine(load_config=lambda: Config(city="Croatá, Ceará", projetos={}), brave_key=lambda: None)


# ── entender comandos ────────────────────────────────────────────────────

@pytest.mark.parametrize("text,intent", [
    ("Jarvis, abre o WhatsApp", "abrir"), ("abra o projeto MeuApp", "abrir"), ("abrir github.com", "abrir"),
    ("que horas são?", "hora"), ("que dia é hoje", "data"),
    ("como está o meu PC?", "pc"), ("quanto de ram estou usando", "pc"),
    ("quais programas estão mais pesados", "processos"),
    ("vai chover hoje?", "clima"), ("clima em Fortaleza", "clima"),
    ("notícias de tecnologia", "noticias"), ("tem vagas para mim?", "vagas"),
    ("pesquise sobre energia solar", "pesquisa"), ("ajuda", "ajuda"),
])
def test_classify_portuguese_commands(local, text, intent):
    assert local.classify(text)[0] == intent


def test_city_and_targets_are_extracted(local):
    assert local.classify("clima em Fortaleza")[1] == {"cidade": "fortaleza"}
    assert local.classify("Jarvis, abre o WhatsApp")[1]["alvo"] == "o whatsapp"


@pytest.mark.parametrize("text,direct", [
    ("abre o WhatsApp", True), ("que horas são", True), ("como está o PC?", True),
    ("abre o projeto e analisa o login", False),  # composto: fica com a IA
    ("pesquise sobre Docker", False),              # pesquisa: IA faz melhor quando disponível
    ("me explica recursão", False), ("x" * 100, False),
])
def test_only_short_direct_commands_skip_the_ai(local, text, direct):
    assert local.is_direct_command(text) is direct


def test_open_routes_to_app_site_folder_or_project(local, monkeypatch):
    from jarvis.pc import launcher

    calls = []
    monkeypatch.setattr(launcher, "open_app", lambda a: calls.append(("app", a)) or "ok")
    monkeypatch.setattr(launcher, "open_site", lambda a: calls.append(("site", a)) or "ok")
    monkeypatch.setattr(launcher, "open_folder", lambda a: calls.append(("pasta", a)) or "ok")
    for text in ("abre o WhatsApp", "abre github.com", "abre a pasta downloads", "abre downloads", "abre o site g1.globo.com"):
        local.handle(text)
    assert calls == [("app", "whatsapp"), ("site", "github.com"), ("pasta", "downloads"),
                     ("pasta", "downloads"), ("site", "g1.globo.com")]


def test_time_and_date_answers(local):
    assert local.handle("que horas são").startswith("Agora são ")
    assert local.handle("que dia é hoje").startswith("Hoje é ")


def test_answer_is_marked_as_independent_mode(local):
    answer = local.ask([{"role": "user", "content": "que horas são"}])
    assert answer.brain == "local" and "sem IA" in answer.text


def test_errors_never_break_the_conversation(local, monkeypatch):
    from jarvis.pc import launcher

    monkeypatch.setattr(launcher, "open_app", lambda a: (_ for _ in ()).throw(ValueError("não encontrei")))
    assert local.handle("abre o programa xyz").startswith("Tentei, mas não consegui")


def test_questions_become_web_research_and_chit_chat_gets_help(local, monkeypatch):
    asked = []
    monkeypatch.setattr(local, "_pesquisa", lambda text, tema="": asked.append(tema) or "resumo")
    assert local.handle("O que é energia solar?") == "resumo" and asked == ["o que e energia solar"]
    assert "Não entendi" in local.handle("valeu")  # antes devolvia o bloco genérico de funções (a queixa do dono); agora admite e oferece caminhos


# ── roteador ─────────────────────────────────────────────────────────────

class Brain:
    def __init__(self, name, fail=False):
        self.name, self.fail, self.calls = name, fail, 0

    def ask(self, messages, system):
        self.calls += 1
        if self.fail:
            raise BrainUnavailable("You've hit your session limit")
        return Answer("resposta da " + self.name, self.name)


def test_jarvis_keeps_working_when_every_ai_is_down(local, monkeypatch):
    monkeypatch.setattr(local, "_pesquisa", lambda text, tema="": "resumo da web")
    router = Router([Brain("claude", True), Brain("gemini", True), local])
    answer = router.ask([{"role": "user", "content": "o que é energia solar?"}], "s")
    assert answer.brain == "local" and "resumo da web" in answer.text


def test_direct_commands_go_local_first_without_spending_ai(local):
    claude = Brain("claude")
    router = Router([claude, local], prefer=lambda t: "local" if local.is_direct_command(t) else None)
    assert router.ask([{"role": "user", "content": "que horas são?"}], "s").brain == "local"
    assert claude.calls == 0
    assert router.ask([{"role": "user", "content": "me ajuda a planejar a semana"}], "s").brain == "claude"


def test_build_router_appends_local_engine_last(monkeypatch, tmp_path):
    from jarvis import brains

    monkeypatch.setattr(brains, "write_mcp_config", lambda path=None: tmp_path / "m.json")
    router = brains.build_router(Config())
    assert [b.name for b in router.brains] == ["claude", "gemini", "nvidia", "llm", "local"]
    # Com modo_independente desligado o motor existe, mas fica invisível (não entra como reserva).
    off = Config(modo_independente=False)
    monkeypatch.setattr("jarvis.config.load", lambda: off)
    router = brains.build_router(off)
    assert [b.name for b in router.order([{"role": "user", "content": "oi"}])] == ["claude", "gemini", "nvidia"]


# ── pesquisa sem IA ──────────────────────────────────────────────────────

def fake_web(routes):
    @contextmanager
    def opener(request, timeout=None):
        url = request.full_url
        for key, body in routes.items():
            if key in url:
                resp = io.BytesIO(body.encode() if isinstance(body, str) else json.dumps(body).encode())
                resp.headers = {"Content-Type": "application/json" if not isinstance(body, str) else "text/html; charset=utf-8"}
                yield resp
                return
        raise OSError("sem rota " + url)
    return opener


@pytest.fixture(autouse=True)
def no_cache_or_wait(monkeypatch):
    websearch._cache.clear()
    monkeypatch.setattr(websearch, "MIN_INTERVAL", 0)


def test_relevance_filters_homonyms_and_unrelated_pages():
    assert websearch.relevant("Docker (software)", "plataforma de contêineres", ["docker"])
    assert not websearch.relevant("Mahatma Gandhi", "serve ao povo", ["docker"])
    terms = websearch.keywords("linguagem de programação Python")
    assert terms == ["linguagem", "programacao", "python"]
    assert websearch.relevant("Python", "Python é uma linguagem de programação", terms)
    assert not websearch.relevant("Monty Python", "grupo de comédia britânico", terms)


def test_question_words_are_not_search_terms():
    assert websearch.keywords("o que é Docker e para que serve?") == ["docker"]


def test_extractive_summary_uses_only_source_sentences_with_citations():
    docs = [(1, "Docker é uma plataforma de contêineres criada em 2013. O tempo hoje está bom para passear."),
            (2, "Contêineres Docker isolam aplicações do sistema. Docker é uma plataforma de contêineres criada em 2013!")]
    chosen = websearch.extract("o que é docker e contêineres", docs)
    texts = [s for s, _ in chosen]
    assert all(any(s in d for _, d in docs) for s in texts)  # nada inventado
    assert not any("passear" in s for s in texts)
    assert len([s for s in texts if "criada em 2013" in s]) == 1  # sem repetir frase quase igual


def test_research_with_wikipedia_and_ddg_without_keys():
    routes = {
        "pt.wikipedia.org/w/rest.php": {"pages": [{"key": "Docker_(software)", "title": "Docker (software)",
                                                    "excerpt": "Docker é um software de contêineres"},
                                                   {"key": "Gandhi", "title": "Mahatma Gandhi", "excerpt": "líder indiano"}]},
        "pt.wikipedia.org/api/rest_v1/page/summary": {"title": "Docker (software)",
                                                      "extract": "Docker é um conjunto de produtos que entrega software em contêineres isolados."},
        "en.wikipedia.org": {"pages": []},
        "api.duckduckgo.com": {"AbstractText": "", "RelatedTopics": []},
    }
    found = websearch.research("o que é Docker?", 5, opener=fake_web(routes))
    assert [r.titulo for r in found["fontes"]] == ["Docker (software)"]
    text = websearch.format_answer("docker", found)
    assert "sem IA" in text and "contêineres isolados. [1]" in text and "Gandhi" not in text


def test_page_text_ignores_menus_scripts_and_footers():
    html = ("<html><nav><p>Menu inicial do site com muitos links aqui</p></nav><script>var x = 'nao';</script>"
            "<article><p>Este é o parágrafo principal do artigo com conteúdo útil.</p></article>"
            "<footer><p>Rodapé com direitos autorais e contatos do site</p></footer></html>")
    text = websearch.page_text("https://x.com", opener=fake_web({"x.com": html}))
    assert text == "Este é o parágrafo principal do artigo com conteúdo útil."


def test_brave_results_are_used_when_key_exists():
    routes = {"api.search.brave.com": {"web": {"results": [{"title": "Docker <strong>docs</strong>",
                                                             "url": "https://docs.docker.com", "description": "Guia oficial"}]}},
              "wikipedia.org": {"pages": []}, "api.duckduckgo.com": {}}
    results = websearch.search("docker", brave_key="chave", opener=fake_web(routes))
    assert results[0].titulo == "Docker docs" and results[0].url == "https://docs.docker.com"
