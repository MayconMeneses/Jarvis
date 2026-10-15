import json

from jarvis import config


def obsidian_file(tmp_path, vaults):
    path = tmp_path / "obsidian.json"
    path.write_text(json.dumps({"vaults": vaults}), encoding="utf-8")
    return path


def test_detects_open_vault_with_accented_path(tmp_path):
    vault = tmp_path / "Área de Trabalho" / "Projetos"
    vault.mkdir(parents=True)
    old = tmp_path / "Antigo"
    old.mkdir()
    f = obsidian_file(tmp_path, {
        "a": {"path": str(old), "ts": 99999, "open": False},
        "b": {"path": str(vault), "ts": 1, "open": True},
        "c": {"path": str(tmp_path / "apagado"), "ts": 5, "open": True},
    })
    assert config.detect_obsidian_vault(f) == str(vault)


def test_no_obsidian_returns_empty(tmp_path):
    assert config.detect_obsidian_vault(tmp_path / "nao-existe.json") == ""


def test_broken_vault_path_is_replaced_by_detected_one(tmp_path, monkeypatch):
    good = tmp_path / "Área" / "Cofre"
    good.mkdir(parents=True)
    monkeypatch.setattr(config, "detect_obsidian_vault", lambda: str(good))
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"obsidian_vault": "C:\\caminho\\quebrado", "city": "Croatá, Ceará"}), encoding="utf-8")
    cfg = config.load(path)
    assert cfg.obsidian_vault == str(good) and cfg.city == "Croatá, Ceará"
    text = path.read_text(encoding="utf-8")
    assert "\\u00c1rea" in text and "Croat\\u00e1" in text  # gravado em ASCII, sem corromper
    assert config.load(path).obsidian_vault == str(good)
