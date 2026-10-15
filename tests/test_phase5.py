import io
import json
from contextlib import contextmanager
from datetime import datetime

import pytest

from jarvis import briefing, memory
from jarvis.__main__ import system_prompt
from jarvis.config import Config
from jarvis.info import news, weather


# ── memória no Obsidian ──────────────────────────────────────────────────

@pytest.fixture
def vault(tmp_path):
    (tmp_path / "MM System Creator").mkdir()
    (tmp_path / "MM System Creator" / "_Next Steps.md").write_text("Falta a tela de login do MM System.", encoding="utf-8")
    (tmp_path / ".obsidian").mkdir()
    (tmp_path / ".obsidian" / "segredo.md").write_text("login token", encoding="utf-8")
    return memory.Vault(tmp_path)


def test_remember_creates_note_with_frontmatter_and_index(vault):
    path = vault.remember("Preferência de vagas", "Prefere vagas remotas de back-end.")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\ntipo: memoria\nresumo: Prefere vagas remotas")
    assert "# Preferência de vagas" in text
    index = (vault.home / memory.INDEX).read_text(encoding="utf-8")
    assert "[[Preferência de vagas]]" in index
    assert vault.index_text() == "- Preferência de vagas: Prefere vagas remotas de back-end."


def test_remember_same_title_updates_and_keeps_creation_date(vault):
    first = vault.remember("Stack", "Usa Python.")
    created = first.read_text(encoding="utf-8").split("criado: ")[1][:10]
    vault.remember("Stack", "Usa Python e TypeScript.")
    text = first.read_text(encoding="utf-8")
    assert "TypeScript" in text and f"criado: {created}" in text
    assert len(vault.memories()) == 1


def test_user_edits_and_deletions_are_reflected(vault):
    path = vault.remember("Cidade", "Mora no Ceará.")
    path.write_text("# Cidade\n\nMora em Fortaleza.\n", encoding="utf-8")  # editado no Obsidian, sem frontmatter
    assert vault.index_text() == "- Cidade: Mora em Fortaleza."
    path.unlink()
    assert vault.index_text() == ""


def test_titles_cannot_escape_the_memory_folder(vault):
    path = vault.remember("../../fora", "x")
    assert path.parent == vault.home / memory.MEMORY_DIR


def test_search_reads_whole_vault_but_skips_obsidian_config(vault):
    hits = vault.search("tela de login")
    assert [h["nota"] for h in hits] == ["MM System Creator\\_Next Steps.md"] or \
           [h["nota"] for h in hits] == ["MM System Creator/_Next Steps.md"]
    assert "login" in hits[0]["trecho"]


def test_search_ignores_accents(vault):
    vault.remember("Ação", "Revisar orçamento")
    assert vault.search("acao orcamento")


def test_read_is_restricted_to_vault_markdown(vault):
    assert "tela de login" in vault.read("MM System Creator/_Next Steps.md")
    for bad in ("../fora.md", ".obsidian/segredo.md", "MM System Creator"):
        with pytest.raises(ValueError):
            vault.read(bad)


def test_diary_appends_timestamped_lines(vault):
    vault.diary("Pedido: clima\ncom quebra")
    vault.diary("Ação executada")
    [day] = (vault.home / "Diário").glob("*.md")
    lines = day.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("# Diário")
    assert lines[-2].endswith("Pedido: clima com quebra") and lines[-1].endswith("Ação executada")


def test_system_prompt_includes_memory_date_and_city(tmp_path):
    v = memory.Vault(tmp_path)
    v.remember("Objetivo", "Conseguir vaga de dev pleno.")
    cfg = Config(obsidian_vault=str(tmp_path), city="Fortaleza, Ceará")
    prompt = system_prompt(cfg)
    assert "Objetivo: Conseguir vaga de dev pleno." in prompt
    assert "Fortaleza, Ceará" in prompt and "lembrar" in prompt
    assert datetime.now().strftime("%d/%m/%Y") in prompt


# ── clima ────────────────────────────────────────────────────────────────

def fake_opener(responses):
    @contextmanager
    def opener(url, timeout=None):
        key = next(k for k in responses if k in (url if isinstance(url, str) else url.full_url))
        yield io.BytesIO(json.dumps(responses[key]).encode())
    return opener


GEO = {"results": [{"name": "Fortaleza", "admin1": "Ceará", "latitude": -3.7, "longitude": -38.5}]}
FORE = {"current": {"temperature_2m": 27.4, "apparent_temperature": 29.1, "weather_code": 2,
                    "relative_humidity_2m": 70, "wind_speed_10m": 18.2},
        "daily": {"temperature_2m_max": [31.2], "temperature_2m_min": [25.8], "precipitation_probability_max": [15]}}


def test_forecast_and_sentence_in_portuguese():
    w = weather.forecast("Fortaleza", opener=fake_opener({"geocoding": GEO, "forecast": FORE}))
    assert w["local"] == "Fortaleza, Ceará" and w["condicao"] == "parcialmente nublado"
    assert weather.sentence(w) == (
        "Em Fortaleza, Ceará agora faz 27°C, parcialmente nublado, com sensação de 29°C. "
        "Hoje a máxima é 31°C e a mínima 26°C, com 15% de chance de chuva."
    )


def test_unknown_city_raises_weather_error():
    with pytest.raises(weather.WeatherError, match="não encontrada"):
        weather.locate("Xyzzy", opener=fake_opener({"geocoding": {"results": []}}))


# ── notícias ─────────────────────────────────────────────────────────────

RSS = b"""<?xml version="1.0"?><rss><channel>
<item><title>Antiga</title><pubDate>Mon, 13 Oct 2026 10:00:00 -0300</pubDate><link>https://a/1</link></item>
<item><title><![CDATA[Nova &amp; <b>importante</b>]]></title><description>&lt;p&gt;Resumo&lt;/p&gt;</description>
<pubDate>Tue, 14 Oct 2026 10:00:00 -0300</pubDate><link>https://a/2</link></item>
</channel></rss>"""


def test_parse_cleans_html_and_entities():
    items = news.parse(RSS, "Portal")
    assert [i["titulo"] for i in items] == ["Antiga", "Nova & importante"]
    assert items[1]["resumo"] == "Resumo"


def test_parse_rejects_xml_entity_bombs():
    bomb = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><rss><item><title>&b;</title></item></rss>'
    with pytest.raises(Exception):
        news.parse(bomb, "x")


def test_headlines_interleave_sources_newest_first_and_survive_failures():
    @contextmanager
    def opener(request, timeout=None):
        if "quebrado" in request.full_url:
            raise OSError("fora do ar")
        source = request.full_url.split("//")[1][0].upper()  # "a" ou "b"
        yield io.BytesIO(RSS.replace(b"Antiga", b"Antiga " + source.encode())
                         .replace(b"Nova", b"Nova " + source.encode()))

    feeds = {"A": "https://a/rss", "B": "https://b/rss", "C": "https://quebrado/rss"}
    result = news.headlines(limit=3, feeds=feeds, opener=opener)
    assert [h["titulo"] for h in result["manchetes"]] == [
        "Nova A & importante", "Nova B & importante", "Antiga A"]
    assert result["avisos"] == ["C: fora do ar"]


def test_duplicate_headlines_across_sources_are_shown_once():
    @contextmanager
    def opener(request, timeout=None):
        yield io.BytesIO(RSS)

    result = news.headlines(limit=5, feeds={"A": "https://a", "B": "https://b"}, opener=opener)
    assert [h["titulo"] for h in result["manchetes"]] == ["Nova & importante", "Antiga"]


# ── saudação ─────────────────────────────────────────────────────────────

def fake_news(kind, limit):
    return {"manchetes": [{"titulo": f"{kind} {i}", "fonte": "F", "resumo": "", "link": ""} for i in range(limit)]}


def test_first_open_of_day_has_weather_news_and_is_saved(tmp_path):
    cfg = Config(user_name="Maycon", city="Fortaleza", obsidian_vault=str(tmp_path))
    state = tmp_path / "estado.json"
    morning = datetime(2026, 10, 14, 8, 0)
    get_w = lambda city: {**{k: 0 for k in ("agora_c", "sensacao_c", "maxima_c", "minima_c")},  # noqa: E731
                          "local": city, "condicao": "céu limpo", "chance_chuva_percent": None}
    first = briefing.build(cfg, morning, state, get_w, fake_news)
    assert first["completo"] and first["text"].startswith("Bom dia, Maycon! Como você está?")
    assert "Em Fortaleza agora faz 0°C, céu limpo" in first["text"]
    assert "• tecnologia 0 (F)" in first["text"]
    assert "Destaques: gerais 0. tecnologia 0." in first["speak"]
    assert list((tmp_path / "Jarvis" / "Relatórios").glob("*Briefing.md"))

    later = briefing.build(cfg, datetime(2026, 10, 14, 19, 0), state, get_w, fake_news)
    assert not later["completo"] and later["text"].startswith("Boa noite")
    assert "•" not in later["text"]


def test_without_city_asks_for_it(tmp_path):
    result = briefing.build(Config(), datetime(2026, 10, 14, 14, 0), tmp_path / "e.json",
                            lambda c: pytest.fail("não deveria buscar clima"), fake_news)
    assert result["text"].startswith("Boa tarde") and "minha cidade é" in result["text"]
