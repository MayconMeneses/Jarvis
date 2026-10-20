import pytest


@pytest.fixture(autouse=True)
def isolated_user_data(tmp_path, monkeypatch):
    """Nenhum teste pode ler ou gravar a memória, a configuração ou as chaves reais do usuário."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("JARVIS_CLAUDE_PROJECTS", str(tmp_path / "claude-projects"))  # o módulo de uso nunca lê o ~/.claude real nos testes
