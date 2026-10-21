import hashlib
import io
import json
import re
from pathlib import Path

import pytest

from jarvis import __version__, proc, updater

DATA = b"MZ instalador de mentira"
SHA = hashlib.sha256(DATA).hexdigest()
URL = updater.DOWNLOAD_PREFIX + "v0.16.0/SuperJarvis-Setup-0.16.0.exe"


class Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def release(digest=f"sha256:{SHA}", name="SuperJarvis-Setup-0.16.0.exe", url=URL):
    return {"body": "novidades", "assets": [{"name": name, "digest": digest, "browser_download_url": url}]}


def opener_for(rel, data=DATA):
    def opener(request, timeout=0):
        return Resp(json.dumps(rel).encode() if request.full_url == updater.API else data)
    return opener


def test_version_matches_installer():
    iss = Path(updater.__file__).parents[1] / "packaging" / "installer.iss"
    assert re.search(rf'#define AppVersion "{re.escape(__version__)}"', iss.read_text(encoding="utf-8"))


def test_version_comparison():
    assert updater.is_newer("v0.16.0", "0.15.0") and updater.is_newer("1.0.0", "0.99.9")
    assert not updater.is_newer("0.15.0", "0.15.0") and not updater.is_newer("0.9.0", "0.15.0")
    assert not updater.is_newer("latest", "0.15.0")


def test_downloads_new_version_and_verifies_hash(tmp_path):
    out = updater.check(tmp_path, "0.15.0", opener_for(release()))
    assert out["estado"] == "pronta" and out["versao"] == "0.16.0"
    assert (tmp_path / "SuperJarvis-Setup-0.16.0.exe").read_bytes() == DATA
    assert updater.pending(tmp_path, "0.15.0")["version"] == "0.16.0"
    again = updater.check(tmp_path, "0.15.0", lambda *a, **k: pytest.fail("não devia baixar de novo"))
    assert again["estado"] == "pronta"


def test_up_to_date_downloads_nothing(tmp_path):
    assert updater.check(tmp_path, "0.16.0", opener_for(release()))["estado"] == "atual"
    assert not list(tmp_path.iterdir())


def test_bad_hash_is_discarded(tmp_path):
    out = updater.check(tmp_path, "0.15.0", opener_for(release(), data=b"adulterado"))
    assert out["estado"] == "erro" and "SHA-256" in out["mensagem"]
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("rel", [
    release(digest=""),                                                  # sem hash publicado
    release(url="https://evil.example/SuperJarvis-Setup-0.16.0.exe"),    # fora do repositório
    release(name="outro.exe"),                                           # nome fora do padrão
    {"assets": []},
])
def test_refuses_unverifiable_releases(tmp_path, rel):
    assert updater.check(tmp_path, "0.15.0", opener_for(rel))["estado"] == "atual"


def test_network_failure_never_raises(tmp_path):
    def broken(*a, **k):
        raise OSError("sem internet")
    assert updater.check(tmp_path, "0.15.0", broken)["estado"] == "erro"


def test_install_runs_only_verified_file_and_cleanup_removes_old(tmp_path):
    updater.check(tmp_path, "0.15.0", opener_for(release()))
    calls = []
    assert updater.install(tmp_path, "0.15.0", lambda cmd, **k: calls.append(cmd)) is True
    assert calls[0][0].endswith("SuperJarvis-Setup-0.16.0.exe") and "/SILENT" in calls[0]
    (tmp_path / "SuperJarvis-Setup-0.16.0.exe").write_bytes(b"trocado")  # adulterado depois do download
    assert updater.install(tmp_path, "0.15.0", lambda *a, **k: calls.append("x")) is False and len(calls) == 1
    updater.cleanup(tmp_path, "0.16.0")  # já instalada: some da pasta
    assert not list(tmp_path.iterdir())


def test_mixin_checks_pushes_card_and_installs(tmp_path, monkeypatch):
    from jarvis.ui.api_update import UpdateMixin

    pushed, quit_calls = [], []

    class Fake(UpdateMixin):
        _cfg = type("C", (), {"atualizacao_automatica": True})()
        _quit = staticmethod(lambda: quit_calls.append(1))
        _push = lambda self, payload: pushed.append(payload)
        _updates_dir = lambda self: tmp_path

    monkeypatch.setattr(updater, "latest_release", lambda opener=None: {
        "version": "0.99.0", "name": "SuperJarvis-Setup-0.99.0.exe", "url": URL, "sha256": SHA, "notes": "n"})
    monkeypatch.setattr(updater, "download", lambda info, folder, opener=None: (
        (folder / info["name"]).write_bytes(DATA),
        (folder / updater.PENDING).write_text(json.dumps({"version": "0.99.0", "file": info["name"], "sha256": SHA})),
        None)[-1])
    api = Fake()
    assert api.check_update()["estado"] == "pronta" and pushed[0]["update"]["versao"] == "0.99.0"
    started = []
    monkeypatch.setattr(proc.subprocess, "Popen", lambda cmd, **k: started.append(cmd))
    assert api.install_update() == {"ok": True} and started and "/SILENT" in started[0]


def test_update_loop_does_nothing_outside_the_installed_app(monkeypatch):
    from jarvis.ui import api_update

    created = []
    monkeypatch.setattr(api_update.threading, "Thread", lambda *a, **k: created.append(1))
    fake = type("F", (api_update.UpdateMixin,), {"_cfg": type("C", (), {"atualizacao_automatica": True})()})()
    fake.start_update_loop()  # não está congelado (PyInstaller): não cria thread
    assert created == []
