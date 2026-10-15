import json

import pytest

from jarvis.brains.base import BrainUnavailable
from jarvis.brains.claude_cli import ClaudeCLI, child_env, parse_output
from jarvis.config import ClaudeConfig


def test_child_env_removes_api_keys_and_nested_session_markers():
    env = {
        "ANTHROPIC_API_KEY": "sk-secret",
        "anthropic_base_url": "http://x",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli",
        "CLAUDE_CODE_GIT_BASH_PATH": r"C:\Git\bin\bash.exe",
        "PATH": "C:\\bin",
    }
    cleaned = child_env(env)
    assert cleaned == {
        "CLAUDE_CODE_GIT_BASH_PATH": r"C:\Git\bin\bash.exe",
        "PATH": "C:\\bin",
    }


def test_command_disables_tools_and_skips_user_settings():
    cmd = ClaudeCLI(ClaudeConfig(executable="claude-inexistente")).command("sys")
    assert cmd[1] == "-p"
    assert cmd[cmd.index("--tools") + 1] == ""
    assert cmd[cmd.index("--setting-sources") + 1] == "project"
    assert "--strict-mcp-config" in cmd
    assert "--bare" not in cmd  # --bare ignora o login da assinatura
    assert "--model" not in cmd


def test_command_passes_configured_model():
    cmd = ClaudeCLI(ClaudeConfig(executable="x", model="sonnet")).command("sys")
    assert cmd[cmd.index("--model") + 1] == "sonnet"


def test_parse_output_returns_result_text():
    out = json.dumps({"type": "result", "is_error": False, "result": " Olá! "})
    answer = parse_output(out, "", 0)
    assert answer.text == "Olá!"
    assert answer.brain == "claude"


@pytest.mark.parametrize(
    "stdout,code",
    [
        (json.dumps({"is_error": True, "result": "limite atingido"}), 1),
        (json.dumps({"is_error": False, "result": "x"}), 2),
        ("não é json", 1),
    ],
)
def test_parse_output_errors_become_brain_unavailable(stdout, code):
    with pytest.raises(BrainUnavailable):
        parse_output(stdout, "erro", code)


def test_missing_executable_is_brain_unavailable(tmp_path):
    brain = ClaudeCLI(ClaudeConfig(executable="claude-inexistente-123"), workdir=tmp_path)
    with pytest.raises(BrainUnavailable):
        brain.ask("oi", "sys")
