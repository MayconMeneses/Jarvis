"""Temas, efeitos e acessibilidade da janela do PC."""

import json
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from jarvis import config
from jarvis.ui import web
from jarvis.ui.api_tema import TEMAS, TemaMixin

CSS = Path(web.__file__).parent / "css"


def _luz(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contraste(a, b):
    x, y = sorted((_luz(a), _luz(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def _tokens():
    base = (CSS / "base.css").read_text(encoding="utf-8")
    design = (CSS / "design.css").read_text(encoding="utf-8")
    pega = lambda txt: dict(re.findall(r"--([\w-]+):\s*(#[0-9a-fA-F]{6})\b", txt))
    temas = {"hud": pega(base.split("}")[0])}
    for nome in TEMAS[1:]:
        bloco = re.search(r':root\[data-tema="%s"\]\s*\{(.*?)\}' % nome, design, re.S).group(1)
        temas[nome] = {**temas["hud"], **pega(bloco)}
    return temas


def test_page_has_reduced_motion_and_design_is_last():
    pagina = web.page()
    assert "prefers-reduced-motion" in pagina and "focus-visible" in pagina and 'id="aurora"' in pagina
    assert web.CSS[-1] == "design"
    assert pagina.rindex("--sp-1") > pagina.rindex("#uso")  # o CSS do design vem depois do último CSS de tela


def test_page_injects_theme_and_effects_and_rejects_garbage():
    cfg = SimpleNamespace(tema="esmeralda", efeitos_visuais="suave")
    assert 'data-tema="esmeralda" data-efeitos="suave"' in web.page(cfg)
    assert 'data-tema="hud" data-efeitos="completo"' in web.page(SimpleNamespace(tema='"><script>', efeitos_visuais=5))
    assert 'data-tema="hud"' in web.page()


def test_old_config_without_theme_loads(tmp_path):
    arquivo = tmp_path / "config.json"
    arquivo.write_text(json.dumps({"user_name": "Ana", "campo_velho": 1}), encoding="utf-8")
    cfg = config.load(arquivo)
    assert cfg.tema == "hud" and cfg.efeitos_visuais == "completo"
    assert json.loads(arquivo.read_text(encoding="utf-8"))["tema"] == "hud"


class _Api(TemaMixin):
    def __init__(self):
        self._cfg = config.Config()

    def _diary(self, texto):
        pass


def test_set_tema_validates(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path)
    api = _Api()
    assert api.set_tema("ambar")["ok"] and api.get_tema()["tema"] == "ambar"
    assert config.load().tema == "ambar"
    for ruim in ("neon", "", None, 3, "<b>"):
        res = api.set_tema(ruim)
        assert not res["ok"] and res["tema"] == "ambar"
    assert config.load().tema == "ambar"


@pytest.mark.parametrize("tema", TEMAS)
def test_theme_contrast_is_wcag_aa(tema):
    t = _tokens()[tema]
    for fundo in ("bg", "panel-solid"):
        for cor in ("text", "muted", "faint", "cyan", "orange", "magenta", "ok", "danger"):
            assert _contraste(t[cor], t[fundo]) >= 4.5, f"{tema}: {cor} sobre {fundo}"
