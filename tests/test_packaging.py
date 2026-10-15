import sys

from jarvis.brains import mcp_server_command


def test_dev_mode_runs_mcp_server_as_module():
    command, args = mcp_server_command()
    assert command.lower().endswith("python.exe") and args == ["-m", "jarvis.mcp_server"]


def test_installed_mode_uses_console_exe_next_to_app(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Jarvis.exe"))
    command, args = mcp_server_command()
    assert command == str(tmp_path / "jarvis-cli.exe") and args == ["--mcp-server"]


def test_second_instance_is_detected():
    from jarvis.ui.app import claim_single_instance

    name = "Local\\SuperJarvisTeste"
    first = claim_single_instance(name)
    assert first is not None
    assert claim_single_instance(name) is None
    import ctypes

    ctypes.windll.kernel32.CloseHandle(first)
    again = claim_single_instance(name)
    assert again is not None
    ctypes.windll.kernel32.CloseHandle(again)
