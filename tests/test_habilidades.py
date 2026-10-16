"""Habilidades de programador: catálogo, avaliação de projetos (somente leitura) e evolução."""

import subprocess

import pytest

from jarvis import memory_db
from jarvis.config import Config
from jarvis.dev import conhecimento, habilidades as H, logica, saber
from jarvis.dev.habilidades import checagens, evolucao, varredura
from jarvis.local.engine import LocalEngine


def write(path, text="", binary=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")


def git(folder, *args):
    subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)


@pytest.fixture
def ruim(tmp_path):
    root = tmp_path / "ruim"
    write(root / "app.py", 'API_KEY = "abcd1234abcd1234abcd5678"\n\ndef rodar(x):\n    try:\n        return eval(x)\n    except:\n        pass\n'
                           'def consulta(db, nome):\n    return db.execute(f"SELECT * FROM t WHERE n = \'{nome}\'")\n# TO' 'DO limpar\n')
    return root


@pytest.fixture
def bom(tmp_path):
    root = tmp_path / "bom"
    leiame = "# Loja\n\n" + "\n".join(f"Linha de explicação {i} do projeto." for i in range(25)) + "\n\n## Como rodar\n\npip install -r requirements.txt\n"
    write(root / "README.md", leiame)
    write(root / "docs" / "decisoes.md", "# Decisões\n")
    write(root / ".gitignore", ".env\n__pycache__/\nnode_modules/\n")
    write(root / "pyproject.toml", "[project]\nname='loja'\n[tool.pytest.ini_options]\ntestpaths=['tests']\n")
    write(root / "uv.lock", "")
    write(root / "src" / "loja.py", 'import logging\n\nlog = logging.getLogger(__name__)\n\n\ndef total(itens):\n    try:\n        return sum(itens)\n    except TypeError:\n        log.error("itens inválidos")\n        raise\n')
    write(root / "src" / "outro.py", "def a():\n    try:\n        return 1\n    except ValueError:\n        return 2\n\n\ndef b():\n    try:\n        return 3\n    except KeyError:\n        return 4\n")
    write(root / "tests" / "test_loja.py", "def test_total():\n    assert True\n")
    write(root / "tests" / "conftest.py", "")
    write(root / ".github" / "workflows" / "ci.yml", "name: ci\n")
    write(root / "Dockerfile", "FROM python\n")
    write(root / "Makefile", "test:\n\tpytest\n")
    write(root / "web" / "index.html", '<!doctype html><html lang="pt-BR"><head><meta name="viewport" content="width=device-width"></head>'
                                       '<body><label for="n">Nome</label><input id="n"><img src="a.png" alt="logo"></body></html>')
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.email", "t@t")
    git(root, "config", "user.name", "t")
    for i in range(5):
        write(root / "docs" / f"nota{i}.md", str(i))
        git(root, "add", ".")
        git(root, "commit", "-q", "-m", f"mudança {i}")
    return root


# ── catálogo ─────────────────────────────────────────────────────────────

def test_catalog_is_complete_and_consistent_with_the_checks():
    items = H.catalogo()
    assert len(items) == 23 and len({i["id"] for i in items}) == 23
    assert {i["id"] for i in items if i["medida"]} == set(checagens.CHECAGENS)
    for item in items:
        assert len(item["niveis"]) == 3 and len(item["praticas"]) >= 4 and item["treino"] and item["resumo"], item["id"]
        for ref in item["estudar"]:
            assert saber.procurar(ref) or conhecimento.lookup(ref), (item["id"], ref)


def test_lookup_levels_checklist_and_plan():
    assert H.habilidade("segurança")["id"] == "seguranca" and H.habilidade("testes")["id"] == "testes" and H.habilidade("xadrez") is None
    assert [H.nivel(n) for n in (10, 60, 90, None)] == ["iniciante", "intermediário", "avançado", "não medido"]
    check = H.checklist("segurança")
    assert "- [ ] Consultas parametrizadas" in check and "iniciante" in check and "avançado" in check
    plano = H.plano("testes")
    assert "Treino da semana" in plano and "Testes automatizados" in plano
    assert "Não conheço esse aspecto" in H.checklist("culinária") and "Diga qual habilidade" in H.plano("culinária")


# ── avaliação ────────────────────────────────────────────────────────────

def test_bad_project_gets_low_scores_with_concrete_suggestions(ruim):
    a = H.analisar(ruim)
    ap = a["aspectos"]
    assert ap["testes"]["nota"] == 0 and ap["documentacao"]["nota"] == 0 and ap["versionamento"]["nota"] == 0
    assert ap["seguranca"]["nota"] <= 60 and any("segredos" in x.lower() for x in ap["seguranca"]["achados"])
    assert any("parametrizadas" in s for s in ap["seguranca"]["sugestoes"]) and any("eval" in s for s in ap["seguranca"]["sugestoes"])
    assert ap["codigo-limpo"]["nota"] < 100 and any("except:" in x for x in ap["codigo-limpo"]["achados"])
    assert ap["acessibilidade"]["nota"] is None  # sem HTML: não se aplica
    assert a["geral"] < 40 and a["aspectos"]["automacao"]["nota"] == 0
    weakest = [i for i, _ in H.mais_fracos(a, 3)]
    assert len(weakest) == 3 and "seguranca" in weakest or "testes" in weakest


def test_good_project_scores_high(bom):
    a = H.analisar(bom)
    ap = a["aspectos"]
    for aspecto in ("documentacao", "versionamento", "seguranca", "automacao", "observabilidade", "acessibilidade", "estrutura"):
        assert ap[aspecto]["nota"] >= 80, (aspecto, ap[aspecto])
    assert ap["testes"]["nota"] >= 70 and a["geral"] >= 80 and H.nivel(a["geral"]) == "avançado"


def test_analysis_never_writes_to_the_project(bom):
    antes = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in bom.rglob("*") if p.is_file() and ".git" not in p.parts}
    H.analisar(bom)
    depois = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in bom.rglob("*") if p.is_file() and ".git" not in p.parts}
    assert antes == depois


def test_scanner_skips_dependencies_respects_gitignore_and_flags_big_files(tmp_path, monkeypatch):
    root = tmp_path / "p"
    write(root / "a.py", "x = 1\n")
    write(root / "node_modules" / "lib" / "x.js", "y")
    write(root / ".venv" / "lib.py", "z")
    write(root / ".gitignore", "segredo/\n*.db\nlocal.txt\n")
    write(root / "segredo" / "chave.py", "K = 1")
    write(root / "dados.db", "x")
    write(root / "local.txt", "x")
    write(root / "peso" / "grande.bin", b"0" * (6 * 1024 * 1024), binary=True)
    write(root / "pkg" / ".gitignore", "interno.py\n")
    write(root / "pkg" / "interno.py", "a = 1")
    write(root / "pkg" / "publico.py", "b = 1")
    p = varredura.escanear(root)
    assert "a.py" in p.arquivos and "pkg/publico.py" in p.arquivos and p.grandes == ["peso/grande.bin"]
    assert not any(x.startswith(("node_modules", ".venv", "segredo")) or x in ("dados.db", "local.txt", "pkg/interno.py") for x in p.arquivos)
    monkeypatch.setattr(varredura, "MAX_ARQUIVOS", 3)
    assert varredura.escanear(root).truncado is True
    with pytest.raises(ValueError, match="não encontrada"):
        varredura.escanear(tmp_path / "nao-existe")


def test_placeholders_tests_and_templates_are_not_flagged_as_secrets(tmp_path):
    root = tmp_path / "p"
    write(root / "cfg.py", 'import os\nAPI_KEY = os.environ["API_KEY"]\nTOKEN = "seu_token_aqui_exemplo_123"\n')
    write(root / "tests" / "test_x.py", 'SENHA = "abcd1234abcd1234abcd"\n')
    write(root / "modelo" / "app.py.tpl", 'SECRET = "abcd1234abcd1234abcd"\n')
    assert H.analisar(root)["aspectos"]["seguranca"]["nota"] == 100


def test_accessibility_check_spots_missing_attributes(tmp_path):
    root = tmp_path / "p"
    write(root / "index.html", "<html><body><img src='a.png'><input name='x'></body></html>")
    ap = H.analisar(root)["aspectos"]["acessibilidade"]
    assert ap["nota"] == 0 and len(ap["sugestoes"]) == 4


# ── evolução ─────────────────────────────────────────────────────────────

@pytest.fixture
def cfg(tmp_path):
    return Config(memoria_db=str(tmp_path / "m.db"))


def test_history_shows_progress_between_evaluations(cfg, bom, ruim):
    mem = memory_db.open_memory(cfg)
    first = evolucao.avaliar(cfg, mem, str(ruim))
    assert "nota geral" in first and "Ainda há uma avaliação só" in first
    write(ruim / "README.md", "# Meu app\n\n" + "\n".join(f"linha {i} sobre o app" for i in range(25)) + "\n\npip install x\n")
    write(ruim / "tests" / "test_app.py", "def test_x():\n    assert True\n")
    second = evolucao.avaliar(cfg, mem, str(ruim))
    assert "Evolução desde" in second and "ponto(s)" in second and "→" in second
    registros = evolucao.historico(mem, "ruim")
    assert len(registros) == 2 and registros[1]["geral"] > registros[0]["geral"]
    assert mem.get("Habilidades/Avaliações/ruim").count("\n{") == 2  # uma linha JSON por avaliação
    assert "Plano para evoluir" in evolucao.proxima(cfg, mem, str(ruim)) and "Ainda não avaliei" in evolucao.proxima(cfg, mem, str(bom))


def test_next_skill_is_the_weakest_of_the_last_evaluation(cfg, ruim):
    mem = memory_db.open_memory(cfg)
    evolucao.avaliar(cfg, mem, str(ruim))
    text = evolucao.proxima(cfg, mem, str(ruim))
    assert "Ponto mais fraco de ruim" in text and "0/100" in text
    assert "Plano para evoluir: Lógica e algoritmos" in evolucao.proxima(cfg, mem, "")


def test_registered_project_names_and_unknown_projects(cfg, bom):
    cfg.projetos["Loja Boa"] = str(bom)
    mem = memory_db.open_memory(cfg)
    assert "Avaliação de bom" in evolucao.avaliar(cfg, mem, "loja boa")
    with pytest.raises(ValueError, match="não cadastrado"):
        evolucao.avaliar(cfg, mem, "Inexistente")


def test_evaluating_jarvis_itself_adds_improvements_to_its_notebook(cfg, ruim, monkeypatch):
    from jarvis import selfimprove

    monkeypatch.setattr(selfimprove, "own_repo", lambda: ruim)
    mem = memory_db.open_memory(cfg)
    text = evolucao.avaliar(cfg, mem, str(ruim))
    assert "Anotei 3 melhoria(s)" in text
    ideas = [i["ideia"] for i in selfimprove.list_ideas(mem)]
    assert len(ideas) == 3 and all(i.startswith("Melhorar ") for i in ideas)
    assert "já estavam no caderno" in evolucao.avaliar(cfg, mem, str(ruim))  # sem duplicar


# ── motor próprio e ferramentas MCP ──────────────────────────────────────

@pytest.fixture
def engine(cfg):
    return LocalEngine(load_config=lambda: cfg, brave_key=lambda: None)


@pytest.mark.parametrize("text, intent", [
    ("avalie o projeto Loja", "avaliar_projeto"), ("revise o código do projeto X", "avaliar_projeto"), ("avalie o seu código", "avaliar_projeto"),
    ("analise C:\\pasta\\app", "avaliar_projeto"), ("quais habilidades de programador você acompanha", "habilidades"),
    ("o que devo estudar?", "evoluir"), ("plano de evolução em testes", "evoluir"), ("qual minha próxima habilidade", "evoluir"),
    ("checklist de segurança", "checklist"),
])
def test_requests_are_classified(engine, text, intent):
    assert engine.classify(text)[0] == intent


def test_engine_answers_without_ai(engine, cfg, bom):
    assert "Checklist: Segurança" in engine.handle("checklist de segurança")
    assert "Plano para evoluir: Testes" in engine.handle("plano de evolução em testes")
    assert "Habilidades de programador" in engine.handle("quais habilidades de programador?")
    assert "Qual projeto devo avaliar" in engine.handle("avalie o projeto")
    cfg.projetos["Loja Boa"] = str(bom)
    assert "nota geral" in engine.handle("avalie o projeto Loja Boa")
    assert "nota geral" in engine.handle(f"avalie {bom}")
    assert "não cadastrado" in engine.handle("avalie o projeto Fantasma")
    assert "Plano para evoluir" in engine.handle("o que devo estudar?")


def test_mcp_tools_are_registered_and_work(cfg, bom, monkeypatch):
    pytest.importorskip("mcp")
    import asyncio

    from jarvis import mcp_server
    from jarvis.mcp_tools import habilidades_tools

    names = {t.name for t in asyncio.run(mcp_server.server.list_tools())}
    assert {"habilidades_de_programador", "avaliar_projeto", "proxima_habilidade", "checklist_de_revisao", "plano_de_evolucao"} <= names
    monkeypatch.setattr("jarvis.config.load", lambda: cfg)
    assert "nota geral" in habilidades_tools.avaliar_projeto(str(bom)) and "não cadastrado" in habilidades_tools.avaliar_projeto("Zzz")
    assert "Checklist" in habilidades_tools.checklist_de_revisao("testes") and "Treino" in habilidades_tools.plano_de_evolucao("testes")
    assert "Habilidades" in habilidades_tools.habilidades_de_programador() and "Ainda não avaliei novo" in habilidades_tools.proxima_habilidade(str(bom.parent / "novo"))


def test_when_everything_measurable_is_great_it_suggests_unmeasured_skills_in_turn(cfg, bom):
    mem = memory_db.open_memory(cfg)
    suggestions = []
    for _ in range(3):
        evolucao.avaliar(cfg, mem, str(bom))
        text = evolucao.proxima(cfg, mem, str(bom))
        assert "Tudo o que eu consigo medir" in text or "Ponto mais fraco" in text
        suggestions.append(text.split("**Plano para evoluir: ")[1].split("**")[0])
    assert len(set(suggestions)) >= 2  # alterna: a evolução não para quando a nota é alta
    assert all(H.habilidade(s)["medida"] is False for s in suggestions if "Tudo o que eu consigo medir" in text)


def test_weekly_training_rotates_through_all_skills(engine):
    from datetime import date

    first_line = lambda w: H.treino_da_semana(date.fromisocalendar(2026, w, 1)).split("\n")[0]  # noqa: E731
    assert len({first_line(w) for w in range(1, 24)}) == 23  # uma habilidade diferente por semana, nas 23
    assert first_line(1) == first_line(24)  # e o rodízio recomeça
    assert engine.classify("qual o treino da semana")[0] == "evoluir" and "Treino da semana" in engine.handle("treino da semana")
