"""Base de conhecimento de programação: consulta, comparação e recomendação (sem IA)."""

import json

import pytest

from jarvis.dev import conhecimento as k

CAMPOS = {"id", "nome", "categoria", "areas", "resumo", "usos", "fortes", "fracos", "quando", "curva", "comeco"}


def test_every_entry_is_complete_and_ids_are_unique():
    ids = [e["id"] for e in k.entries()]
    assert len(ids) == len(set(ids)) and len(ids) >= 40
    for e in k.entries():
        assert CAMPOS <= set(e), e["id"]
        assert all(e[c] for c in ("resumo", "curva")) and all(e[c] for c in ("usos", "fortes", "fracos", "quando", "comeco")), e["id"]
        assert e["categoria"] in k.CATEGORIAS and set(e["areas"]) <= set(k.AREAS), e["id"]


def test_covers_the_main_languages_and_frameworks_for_each_area():
    for needed in ("javascript", "typescript", "python", "java", "csharp", "php", "go", "sql", "html", "css", "react", "vue",
                   "angular", "nextjs", "nodejs", "express", "fastapi", "django", "flask", "spring", "laravel", "postgresql",
                   "mongodb", "mern"):
        assert k.lookup(needed), needed
    assert {"react", "vue", "angular"} <= {e["id"] for e in k.by_area("front end")}
    assert {"fastapi", "django", "spring"} <= {e["id"] for e in k.by_area("back end")}
    assert {"nextjs", "mern", "python-react"} <= {e["id"] for e in k.by_area("full stack")}
    assert {"postgresql", "sqlite"} <= {e["id"] for e in k.by_area("bancos de dados")}


def test_system_types_point_to_known_technologies_and_templates():
    from jarvis.dev import modelos

    for kind in k.system_types():
        for key in ("front", "back", "banco"):
            assert all(k.lookup(i) for i in kind[key]), (kind["id"], key)
        if kind["modelo"]:
            assert modelos.normalize(kind["modelo"]) == kind["modelo"]
        assert kind["motivo"] and kind["palavras"]


@pytest.mark.parametrize("term, expected", [
    ("Python", "python"), ("a linguagem Python?", "python"), ("o framework React.", "react"), ("c#", "csharp"), (".NET", "csharp"),
    ("next.js", "nextjs"), ("Next", "nextjs"), ("postgres", "postgresql"), ("Spring Boot", "spring"), ("golang", "go"),
    ("TS", "typescript"), ("FastAPI", "fastapi"),
])
def test_lookup_accepts_names_aliases_and_articles(term, expected):
    assert k.lookup(term)["id"] == expected


def test_lookup_returns_none_for_unknown_terms():
    assert k.lookup("xadrez") is None and k.lookup("") is None


def test_mentioned_finds_whole_words_in_order():
    assert [e["id"] for e in k.mentioned("compare Python e Node.js com React e Vue")] == ["python", "nodejs", "react", "vue"]
    assert [e["id"] for e in k.mentioned("go, c# e java")] == ["go", "csharp", "java"]
    assert k.mentioned("vamos ao logo da pagina") == []  # "go" dentro de outra palavra não conta


def test_describe_and_compare_are_readable():
    text = k.describe(k.lookup("fastapi"))
    assert text.startswith("**FastAPI**") and "Pontos fortes" in text and "uvicorn" in text
    both = k.compare(k.lookup("django"), k.lookup("fastapi"))
    assert "Django × FastAPI" in both and "Quando escolher" in both


@pytest.mark.parametrize("text, kind", [
    ("quero uma loja virtual para vender roupas", "loja"), ("sistema de gestão de estoque", "gestao"),
    ("preciso de uma API", "api"), ("um dashboard com gráficos", "dashboard"), ("aplicativo de celular", "mobile"),
    ("um chat em tempo real", "tempo-real"), ("landing page", "site"), ("automação de planilhas com python", "automacao"),
])
def test_match_type(text, kind):
    assert k.match_type(text)["id"] == kind


def test_recommend_explains_why_and_offers_a_template_when_there_is_one():
    text = k.recommend("sistema de gestão")
    assert "Front-end" in text and "Back-end" in text and "Banco de dados" in text and "Por quê" in text
    assert "modelo `fastapi+react`" in text
    assert "modelo" not in k.recommend("loja virtual")  # sem modelo pronto: não promete o que não existe
    assert "Não entendi" in k.recommend("xyz abc") and "loja virtual" in k.recommend("xyz abc")


def test_overview_by_area_and_unknown_area():
    assert "React" in k.overview("front end") and "FastAPI" in k.overview("back-end")
    assert "Não conheço essa área" in k.overview("culinária")


def test_data_files_are_valid_utf8_json():
    for path in k.DADOS.glob("*.json"):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), list), path.name
