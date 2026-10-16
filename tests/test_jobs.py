import io
import json
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from jarvis.info import jobs
from jarvis.info.jobs import Job

ISSUES = [
    {"number": 7, "title": "[Remoto] Desenvolvedor Python Júnior na Acme", "html_url": "https://github.com/x/vagas/issues/7",
     "created_at": "2026-10-14T10:00:00Z", "labels": [{"name": "Remoto"}, {"name": "Júnior"}], "body": "## Stack\n- **Python**\n- Django"},
    {"number": 8, "title": "docs: corrige README", "pull_request": {}, "labels": [], "created_at": "2026-10-14T10:00:00Z"},
]
REMOTIVE = {"jobs": [{"id": 99, "title": "Senior React Engineer", "url": "https://remotive.com/remote-jobs/99",
                      "candidate_required_location": "Worldwide", "publication_date": "2026-10-13T08:00:00",
                      "tags": ["react", "typescript"], "company_name": "Globex", "description": "<p>Build UIs</p>"}]}


def opener_for(routes, calls=None):
    @contextmanager
    def opener(request, timeout=None):
        url = request.full_url
        if calls is not None:
            calls.append(url)
        for key, value in routes.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                yield io.BytesIO(json.dumps(value).encode())
                return
        raise OSError(f"sem rota para {url}")
    return opener


def test_github_issues_become_jobs_and_prs_are_skipped():
    [job] = jobs.from_github("x/vagas", opener_for({"api.github.com": ISSUES}))
    assert job.id == "gh:x/vagas#7" and job.local == "Remoto"
    assert job.titulo == "Desenvolvedor Python Júnior na Acme"
    assert job.etiquetas == ["Remoto", "Júnior"] and "Python" in job.descricao and "**" not in job.descricao


def test_remotive_jobs_credit_the_source_and_keep_link():
    [job] = jobs.from_remotive(opener_for({"remotive.com": REMOTIVE}))
    assert job.fonte == "Remotive" and job.link == "https://remotive.com/remote-jobs/99"
    assert job.local == "Remoto (Worldwide)" and job.descricao == "Build UIs"


def test_collect_uses_cache_for_six_hours_and_reports_broken_sources(tmp_path):
    calls = []
    routes = {"frontendbr": ISSUES, "backend-br": OSError("fora do ar"), "react-brasil": [], "remotive.com": REMOTIVE}
    cache = tmp_path / "cache.json"
    first = jobs.collect(cache, now=1000.0, opener=opener_for(routes, calls))
    assert len(first["vagas"]) == 2 and any("backend-br" in a for a in first["avisos"])
    n = len(calls)
    jobs.collect(cache, now=1000.0 + 5 * 3600, opener=opener_for(routes, calls))
    assert len(calls) == n  # dentro de 6 h: nenhuma consulta nova (termos da Remotive)
    jobs.collect(cache, now=1000.0 + 7 * 3600, opener=opener_for(routes, calls))
    assert len(calls) == 2 * n


# ── perfil ───────────────────────────────────────────────────────────────

def test_template_is_created_empty(tmp_path):
    profile, path = jobs.load_profile(tmp_path)
    assert path.exists() and jobs.profile_is_empty(profile)


def test_update_profile_fills_fields_and_rejects_unknown(tmp_path):
    jobs.update_profile(tmp_path, "nivel", "Júnior")
    jobs.update_profile(tmp_path, "Stack", "Python, React; SQL")
    profile, path = jobs.load_profile(tmp_path)
    assert profile["nivel"] == "junior" and profile["stack"] == ["Python", "React", "SQL"]
    assert "Nível: Júnior" in path.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        jobs.update_profile(tmp_path, "Salário", "10k")


# ── pontuação ────────────────────────────────────────────────────────────

NOW = datetime(2026, 10, 15, tzinfo=timezone.utc)
PROFILE = {"stack": ["Python", "Django", "React"], "nivel": "junior", "modalidade": "remoto",
           "cidade": "Fortaleza", "evitar": ["PHP"], "ingles": "basico"}


def job(**kw):
    base = dict(id="gh:x#1", titulo="Desenvolvedor Python Júnior", local="Remoto", fonte="GitHub x",
                link="https://x", publicada="2026-10-14T10:00:00Z", etiquetas=["Remoto"], descricao="Django")
    base.update(kw)
    return Job(**base)


def test_good_match_scores_high_with_reasons():
    points, reasons = jobs.score(job(), PROFILE, NOW)
    assert points >= 80
    assert "usa Python, Django" in reasons and "nível junior" in reasons and "remota" in reasons


def test_senior_role_for_junior_profile_is_penalized():
    points, reasons = jobs.score(job(titulo="Desenvolvedor Python Sênior", etiquetas=["Remoto"]), PROFILE, NOW)
    assert "pede nível sênior" in reasons and points < jobs.score(job(), PROFILE, NOW)[0]


def test_avoided_stack_and_onsite_elsewhere_drop_below_threshold():
    points, reasons = jobs.score(job(titulo="Dev PHP Júnior", local="São Paulo, SP", etiquetas=[], descricao="PHP"), PROFILE, NOW)
    assert points < jobs.MIN_SCORE and any("evitar" in r for r in reasons)


def test_onsite_in_users_city_is_fine_for_remote_profile():
    _, reasons = jobs.score(job(local="Fortaleza, CE", etiquetas=[]), PROFILE, NOW)
    assert "em Fortaleza" in reasons


def test_short_words_do_not_match_inside_other_words():
    # "Go" não deve casar com "Google"; "SQL" não casa com "PostgreSQL" por acidente de substring.
    points, reasons = jobs.score(job(titulo="Analista Google Ads", descricao="", etiquetas=[]),
                                 {**PROFILE, "stack": ["Go"]}, NOW)
    assert not any(r.startswith("usa") for r in reasons)


# ── seleção e vagas já vistas ────────────────────────────────────────────

def test_find_ranks_marks_seen_and_only_new_hides_repeats(tmp_path):
    collected = {"vagas": [job(), job(id="gh:x#2", titulo="Dev PHP", descricao="PHP", etiquetas=[], local="SP")],
                 "avisos": []}
    seen = jobs.SeenStore(tmp_path / "vistas.json")
    first = jobs.find(PROFILE, collected=collected, seen=seen)
    assert [j["id"] for j in first["vagas"]] == ["gh:x#1"] and first["vagas"][0]["nova"]
    again = jobs.find(PROFILE, only_new=True, collected=collected, seen=seen)
    assert again["vagas"] == []
    shown_again = jobs.find(PROFILE, collected=collected, seen=seen)
    assert shown_again["vagas"][0]["nova"] is False


def test_open_link_only_allows_http(monkeypatch):
    pytest.importorskip("webview")
    from jarvis.ui.api import Api
    from jarvis.config import Config

    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url) or True)
    api = Api(Config(), conversation=None)
    assert api.open_link("https://remotive.com/x") is True
    for bad in ("file:///C:/Windows/System32", "javascript:alert(1)", "ms-settings:"):
        assert api.open_link(bad) is False
    assert opened == ["https://remotive.com/x"]


def test_briefing_includes_new_jobs(tmp_path):
    from jarvis import briefing
    from jarvis.config import Config

    cfg = Config(city="", obsidian_vault=str(tmp_path))
    result = briefing.build(cfg, datetime(2026, 10, 15, 9), tmp_path / "e.json",
                            lambda c: {}, lambda k, n: {"manchetes": []},
                            lambda c: ("\n**Vagas novas para você:**\n• Dev Python", "Encontrei 1 vagas novas."))
    assert "Vagas novas para você" in result["text"] and "Encontrei 1 vagas novas." in result["speak"]
