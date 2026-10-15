import json
import subprocess
import types

import pytest

from jarvis import memory
from jarvis.config import ClaudeConfig, Config
from jarvis.dev import projects, runs
from jarvis.pc import actions


def git(path, *args):
    subprocess.run(["git", *args], cwd=path, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    path = tmp_path / "MeuApp"
    path.mkdir()
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.email", "t@t")
    git(path, "config", "user.name", "t")
    (path / "app.py").write_text("print('oi')\n")
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "primeiro commit")
    return path


@pytest.fixture
def cfg(repo, tmp_path):
    plain = tmp_path / "SemGit"
    plain.mkdir()
    return Config(projetos={"Comandiva Sistema": str(repo), "Sem Git": str(plain)})


# ── projetos ─────────────────────────────────────────────────────────────

def test_resolve_ignores_case_and_accents(cfg, repo):
    assert projects.resolve(cfg, "comandiva SISTEMA")[1] == repo
    with pytest.raises(ValueError, match="não cadastrado"):
        projects.resolve(cfg, "outro")


def test_register_requires_existing_absolute_folder(tmp_path):
    c = Config()
    projects.register(c, "X", str(tmp_path))
    assert c.projetos["X"] == str(tmp_path.resolve())
    for bad in ("relativo\\pasta", str(tmp_path / "nao-existe")):
        with pytest.raises(ValueError):
            projects.register(c, "Y", bad)


def test_status_shows_branch_changes_and_commits(cfg, repo):
    (repo / "app.py").write_text("print('mudou')\n")
    info = projects.status(cfg, "Comandiva Sistema")
    assert info["branch"] == "main" and info["arquivos_alterados"] == 1
    assert "primeiro commit" in info["ultimos_commits"][0]
    assert projects.status(cfg, "Sem Git")["git"] == "não é um repositório git"


# ── fila ─────────────────────────────────────────────────────────────────

def test_execute_mode_requires_git_but_analysis_does_not(cfg, tmp_path):
    store = runs.RunStore(tmp_path / "runs")
    with pytest.raises(ValueError, match="git"):
        runs.enqueue(store, cfg, "Sem Git", "executar", "refatorar")
    assert runs.enqueue(store, cfg, "Sem Git", "analisar", "o que faz?").status == "na_fila"
    with pytest.raises(ValueError):
        runs.enqueue(store, cfg, "Sem Git", "apagar_tudo", "x")


def test_read_only_modes_cannot_edit_and_nothing_bypasses_permissions():
    for modo in ("analisar", "planejar"):
        cmd = runs.command(runs.Run("p", ".", modo, "t"), ClaudeConfig(executable="x"))
        assert cmd[cmd.index("--tools") + 1] == "Read,Glob,Grep"
        assert cmd[cmd.index("--permission-mode") + 1] == "dontAsk"
    cmd = runs.command(runs.Run("p", ".", "executar", "t"), ClaudeConfig(executable="x"))
    allowed = cmd[cmd.index("--allowedTools") + 1]
    assert "Bash(git diff:*)" in allowed
    assert "Bash" not in allowed.split(",")  # Bash irrestrito nunca é liberado
    assert "bypassPermissions" not in cmd and "--dangerously-skip-permissions" not in cmd
    assert cmd[cmd.index("--permission-mode") + 1] == "acceptEdits"


def fake_runner(result="Tudo certo", code=0, is_error=False, edit=None):
    calls = []

    def runner(cmd, **kw):
        calls.append((cmd, kw))
        if edit:
            edit()
        return types.SimpleNamespace(returncode=code, stdout=json.dumps({"result": result, "is_error": is_error}), stderr="")
    runner.calls = calls
    return runner


def test_execute_runs_in_project_folder_without_api_key_and_saves_report(cfg, repo, tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-nao-pode-vazar")
    store = runs.RunStore(tmp_path / "runs")
    vault = memory.Vault(tmp_path / "cofre")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "planejar", "tela de login")
    runner = fake_runner("1. Criar rota\n2. Testar")
    done = runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner, vault=vault)
    cmd, kw = runner.calls[0]
    assert kw["cwd"] == str(repo) and "ANTHROPIC_API_KEY" not in kw["env"]
    assert "tela de login" in kw["input"] and "Não altere" in kw["input"]
    assert done.status == "concluida" and done.resultado.startswith("1. Criar rota")
    [report] = (vault.home / "Projetos" / "Comandiva Sistema").glob("*Plano.md")
    assert "tela de login" in report.read_text(encoding="utf-8")


def test_execute_mode_reports_changed_files(cfg, repo, tmp_path):
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "executar", "mudar print")
    runner = fake_runner("Alterei app.py", edit=lambda: (repo / "app.py").write_text("print('novo')\n"))
    done = runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner)
    assert "app.py" in done.alteracoes and "NÃO faça commit" in runner.calls[0][1]["input"]


@pytest.mark.parametrize("runner,expected", [
    (fake_runner(is_error=True, result="limite atingido", code=1), "limite atingido"),
    (fake_runner(result="", code=1), "código 1"),
])
def test_failures_are_recorded(cfg, tmp_path, runner, expected):
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "x")
    done = runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner)
    assert done.status == "falhou" and expected in done.resultado


def test_timeout_is_recorded(cfg, tmp_path):
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "x")
    assert "Tempo esgotado" in runs.execute(run, store, ClaudeConfig(executable="x"), runner=slow).resultado


def test_worker_runs_one_task_and_notifies_once(cfg, tmp_path, monkeypatch):
    store = runs.RunStore(tmp_path / "runs")
    runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "a")
    runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "b")
    monkeypatch.setattr(runs, "execute", lambda run, s, c, vault=None: (
        setattr(run, "status", "concluida"), setattr(run, "resultado", "ok"), s.save(run))[-1])
    notified = []
    worker = runs.RunWorker(store, ClaudeConfig(), notified.append)
    worker.tick()
    assert [r.tarefa for r in notified] == ["a"]
    worker.tick()
    worker.tick()
    assert [r.tarefa for r in notified] == ["a", "b"]


def test_interrupted_tasks_become_failures(cfg, tmp_path):
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "x")
    run.status = "rodando"
    store.save(run)
    store.recover_interrupted()
    assert store.all()[0].status == "falhou"


def test_code_changes_only_enter_queue_after_approval(cfg, tmp_path, monkeypatch):
    acts = actions.ActionStore(tmp_path / "acoes")
    run_store = runs.RunStore(tmp_path / "runs")
    monkeypatch.setattr(runs, "RunStore", lambda: run_store)
    monkeypatch.setattr("jarvis.config.load", lambda: cfg)

    action = actions.propose_dev_task(acts, cfg, "Comandiva Sistema", "criar tela de login", "pedido do usuário")
    assert "ALTERAR" in action.descricao and run_store.all() == []
    done = actions.decide(acts, action.id, True)
    assert done.status == "executada", done.resultado
    [queued] = run_store.all()
    assert queued.modo == "executar" and queued.tarefa == "criar tela de login"

    with pytest.raises(ValueError, match="git"):
        actions.propose_dev_task(acts, cfg, "Sem Git", "x", "m")


# ── ficha do projeto e projeto novo ──────────────────────────────────────

def test_project_info_accumulates_and_description_replaces(cfg, tmp_path):
    vault = memory.Vault(tmp_path / "cofre")
    projects.add_info(cfg, vault, "comandiva sistema", "Sistema de pedidos para restaurantes", "descricao")
    projects.add_info(cfg, vault, "Comandiva Sistema", "Python 3.11 e FastAPI", "Stack")
    projects.add_info(cfg, vault, "Comandiva Sistema", "Usar Postgres", "decisões")
    path = projects.add_info(cfg, vault, "Comandiva Sistema", "Sistema de comandas", "Descrição")
    projects.add_info(cfg, vault, "Comandiva Sistema", "Sem Redis por enquanto", "Decisões")
    text = projects.read_info(cfg, vault, "Comandiva Sistema")
    assert path == vault.home / "Projetos" / "Comandiva Sistema" / "Sobre.md"
    assert "Sistema de comandas" in text and "restaurantes" not in text
    assert "Usar Postgres" in text and "Sem Redis" in text and "## Stack" in text
    assert text.index("## Descrição") < text.index("## Stack") < text.index("## Decisões")
    with pytest.raises(ValueError, match="seção"):
        projects.add_info(cfg, vault, "Comandiva Sistema", "x", "Senhas")
    with pytest.raises(ValueError, match="não cadastrado"):
        projects.add_info(cfg, vault, "Outro", "x")


def test_user_edits_to_the_note_are_kept(cfg, tmp_path):
    vault = memory.Vault(tmp_path / "cofre")
    path = projects.add_info(cfg, vault, "Comandiva Sistema", "primeira", "Pendências")
    path.write_text(path.read_text(encoding="utf-8") + "\n## Links\n- https://exemplo.com\n", encoding="utf-8")
    projects.add_info(cfg, vault, "Comandiva Sistema", "segunda", "Pendências")
    text = path.read_text(encoding="utf-8")
    assert "primeira" in text and "segunda" in text and "## Links" in text and "exemplo.com" in text


def test_tasks_receive_the_project_note_as_context(cfg, tmp_path):
    vault = memory.Vault(tmp_path / "cofre")
    projects.add_info(cfg, vault, "Comandiva Sistema", "Usa FastAPI", "Stack")
    store = runs.RunStore(tmp_path / "runs")
    run = runs.enqueue(store, cfg, "Comandiva Sistema", "analisar", "onde fica o login?")
    runner = fake_runner("em app.py")
    runs.execute(run, store, ClaudeConfig(executable="x"), runner=runner, vault=vault)
    prompt = runner.calls[0][1]["input"]
    assert "Usa FastAPI" in prompt and "não ordem" in prompt and "onde fica o login?" in prompt


def test_unregister_keeps_files(cfg, repo):
    assert projects.unregister(cfg, "comandiva sistema") == "Comandiva Sistema"
    assert "Comandiva Sistema" not in cfg.projetos and (repo / "app.py").exists()
    with pytest.raises(ValueError):
        projects.unregister(cfg, "Comandiva Sistema")


def test_plan_new_validates(cfg, tmp_path, repo):
    assert projects.plan_new(cfg, "Loja: Nova", str(tmp_path)) == tmp_path.resolve() / "Loja Nova"
    with pytest.raises(ValueError, match="já existe um projeto"):
        projects.plan_new(cfg, "comandiva sistema", str(tmp_path))
    with pytest.raises(ValueError, match="já existe uma pasta"):
        projects.plan_new(cfg, "MeuApp", str(repo.parent))
    with pytest.raises(ValueError, match="não encontrada"):
        projects.plan_new(cfg, "X", "pasta/relativa")
    with pytest.raises(ValueError, match="nome"):
        projects.plan_new(cfg, " :: ", str(tmp_path))


def test_new_project_is_only_created_after_approval(cfg, tmp_path, monkeypatch):
    acts = actions.ActionStore(tmp_path / "acoes")
    parent = tmp_path / "Projetos"
    parent.mkdir()
    vault_dir = tmp_path / "cofre"
    vault_dir.mkdir()
    cfg.obsidian_vault = str(vault_dir)
    saved = []
    monkeypatch.setattr("jarvis.config.load", lambda: cfg)
    monkeypatch.setattr("jarvis.config.save", lambda c, path=None: saved.append(dict(c.projetos)))

    action = actions.propose_new_project(acts, cfg, "Loja Virtual", str(parent), "Loja de roupas online", "pedido")
    assert not (parent / "Loja Virtual").exists() and "Loja Virtual" not in cfg.projetos
    done = actions.decide(acts, action.id, True)
    assert done.status == "executada", done.resultado
    target = parent / "Loja Virtual"
    assert "Loja de roupas online" in (target / "README.md").read_text(encoding="utf-8")
    assert projects.is_git_repo(target) and projects.status(cfg, "loja virtual")["ultimos_commits"] == []
    assert saved and saved[-1]["Loja Virtual"] == str(target.resolve())
    assert "Loja de roupas online" in projects.read_info(cfg, memory.Vault(vault_dir), "Loja Virtual")

    # recusada: nada é criado
    other = actions.propose_new_project(acts, cfg, "Outro", str(parent), "", "pedido")
    assert actions.decide(acts, other.id, False).status == "recusada"
    assert not (parent / "Outro").exists()
