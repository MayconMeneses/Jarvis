"""Modelos de projeto: geração dos arquivos e criação do projeto só depois da aprovação."""

import ast
import json

import pytest

from jarvis.config import Config
from jarvis.dev import modelos, projects
from jarvis.pc import actions

COMBOS = [f"{b}+{f}" for b in modelos.BACKS for f in modelos.FRONTS] + list(modelos.BACKS) + list(modelos.FRONTS)


@pytest.mark.parametrize("texto, esperado", [
    ("fastapi+react", "fastapi+react"), ("FastAPI e React", "fastapi+react"), ("node com html", "express+html"),
    ("python", "fastapi"), ("Express / Vite", "express+react"), ("vanilla", "html"), ("react+fastapi", "fastapi+react"),
])
def test_normalize_accepts_natural_names_in_any_order(texto, esperado):
    assert modelos.normalize(texto) == esperado


@pytest.mark.parametrize("texto", ["django+vue", "", "fastapi+express", "cobol"])
def test_invalid_models_explain_the_options(texto):
    with pytest.raises(ValueError, match="(fastapi|stack)"):
        modelos.parse(texto)


@pytest.mark.parametrize("modelo", COMBOS)
def test_every_model_generates_a_consistent_project(modelo):
    files = modelos.arquivos(modelo, "Loja Virtual", "Loja de roupas")
    back, front = modelos.parse(modelo)
    assert {"README.md", ".gitignore"} <= set(files)
    assert any(p.startswith("backend/") for p in files) == bool(back)
    assert any(p.startswith("frontend/") for p in files) == bool(front)
    assert all("__NOME__" not in text and "__SLUG__" not in text and "__DESCRICAO__" not in text for text in files.values())
    assert "Loja Virtual" in files["README.md"] and "Loja de roupas" in files["README.md"]
    for path, text in files.items():  # nada de arquivo vazio, e o que é código tem que ser válido
        assert text.strip(), path
        if path.endswith(".py"):
            ast.parse(text)
        if path.endswith(".json"):
            json.loads(text)


def test_slug_and_package_names():
    assert modelos.slug("Loja Virtual — Ação!") == "loja-virtual-acao"
    assert json.loads(modelos.arquivos("express", "Minha Loja")["backend/package.json"])["name"] == "minha-loja-backend"


def test_all_backs_and_fronts_share_the_same_api_contract():
    for back in modelos.BACKS:
        code = "\n".join(t for p, t in modelos.arquivos(back, "X").items() if p.startswith("backend/") and "test" not in p)
        for route in ("/api/saude", "/api/itens"):
            assert route in code, (back, route)
    for front in modelos.FRONTS:
        code = "\n".join(t for p, t in modelos.arquivos(front, "X").items() if p.startswith("frontend/"))
        assert "/api/itens" in code and "localhost:8000" in code and "PATCH" in code and "DELETE" in code


def test_readme_explains_how_to_run_each_chosen_piece():
    readme = modelos.arquivos("fastapi+react", "Loja")["README.md"]
    assert "uvicorn main:app --reload" in readme and "npm run dev" in readme and "http://localhost:5173" in readme
    readme = modelos.arquivos("express+html", "Loja")["README.md"]
    assert "npm start" in readme and "http.server 8080" in readme and "uvicorn" not in readme


def test_user_text_cannot_inject_into_templates():
    files = modelos.arquivos("fastapi+html", 'Loja "<script>"', "x")
    assert '<script>' not in files["frontend/index.html"].replace('<script src="app.js"></script>', "")


# ── criação com aprovação ────────────────────────────────────────────────

@pytest.fixture
def cfg(tmp_path):
    return Config(memoria_db=str(tmp_path / "m.db"))


def test_create_writes_the_model_registers_the_project_and_starts_git(cfg, tmp_path):
    parent = tmp_path / "Projetos"
    parent.mkdir()
    target = projects.create(cfg, "Loja Virtual", str(parent), "Loja de roupas", modelo="fastapi+react")
    assert (target / "backend" / "main.py").exists() and (target / "frontend" / "src" / "App.jsx").exists()
    assert (target / ".git").is_dir() and cfg.projetos["Loja Virtual"] == str(target)


def test_invalid_model_fails_before_creating_anything(cfg, tmp_path):
    with pytest.raises(ValueError):
        projects.create(cfg, "Loja", str(tmp_path), modelo="django+vue")
    assert not (tmp_path / "Loja").exists() and "Loja" not in cfg.projetos


def test_without_a_model_it_is_still_just_a_readme(cfg, tmp_path):
    target = projects.create(cfg, "Simples", str(tmp_path), "só um README")
    assert sorted(p.name for p in target.iterdir() if p.name != ".git") == ["README.md"]


def test_proposal_does_not_touch_the_disk_and_execution_needs_approval(cfg, tmp_path, monkeypatch):
    acts = actions.ActionStore(tmp_path / "acoes")
    parent = tmp_path / "Projetos"
    parent.mkdir()
    monkeypatch.setattr("jarvis.config.load", lambda: cfg)
    monkeypatch.setattr("jarvis.config.save", lambda c, path=None: None)

    action = actions.propose_new_project(acts, cfg, "Loja Virtual", str(parent), "Loja", "pedido", "FastAPI e React")
    assert "FastAPI (Python) + React (Vite)" in action.descricao and action.params["modelo"] == "fastapi+react"
    assert not (parent / "Loja Virtual").exists()  # só propôs

    done = actions.decide(acts, action.id, True)
    assert done.status == "executada", done.resultado
    assert "README.md explica" in done.resultado and (parent / "Loja Virtual" / "backend" / "main.py").exists()
    from jarvis import memory_db

    ficha = projects.read_info(cfg, memory_db.open_memory(cfg), "Loja Virtual")
    assert "FastAPI (Python) + React (Vite)" in ficha and "## Stack" in ficha  # a stack fica na ficha do projeto

    other = actions.propose_new_project(acts, cfg, "Outro", str(parent), "", "pedido", "express")
    assert actions.decide(acts, other.id, False).status == "recusada" and not (parent / "Outro").exists()


def test_proposal_rejects_unknown_models(cfg, tmp_path):
    with pytest.raises(ValueError, match="django"):
        actions.propose_new_project(actions.ActionStore(tmp_path / "a"), cfg, "X", str(tmp_path), "", "m", "django")
