import base64
import json
import re

import pytest

from jarvis import dashboard
from jarvis.config import Config

PANEL = ('<!doctype html><html><head><script type="module">window.__abrirArquivo = () => {};</script>'
         '</head><body><main id="app"></main></body></html>')


@pytest.fixture
def panel(tmp_path):
    path = tmp_path / "painel" / "index.html"
    path.parent.mkdir()
    path.write_text(PANEL, encoding="utf-8")
    return path


@pytest.fixture
def cfg(panel):
    return Config(painel_dashboard=str(panel))


def loader_args(html: str) -> tuple[str, bytes]:
    m = re.search(r'<script type="module">window\.__abrirArquivo\((.*?), "([A-Za-z0-9+/=]*)"\);</script>', html)
    assert m, "script de carga não encontrado"
    return json.loads(m.group(1).replace("<\\/", "</")), base64.b64decode(m.group(2))


def test_build_embeds_the_document_after_the_panel_script(cfg, tmp_path):
    doc = tmp_path / "vendas.csv"
    doc.write_bytes("mês;total\njan;10\n".encode("utf-8"))
    out = dashboard.build(cfg, str(doc), out_dir=tmp_path / "saida")
    html = out.read_text(encoding="utf-8")
    assert out.parent == tmp_path / "saida" and out.suffix == ".html" and "vendas" in out.name
    assert html.index("window.__abrirArquivo = ") < html.index("window.__abrirArquivo(") < html.index("</body>")
    assert loader_args(html) == ("vendas.csv", doc.read_bytes())
    assert doc.read_bytes() == "mês;total\njan;10\n".encode("utf-8")  # documento intacto


def test_file_name_cannot_close_the_script_tag():
    escaped = dashboard._js_string('a</script><b>.json')
    assert "</" not in escaped and json.loads(escaped.replace("<\\/", "</")) == "a</script><b>.json"


def test_binary_formats_round_trip(cfg, tmp_path):
    doc = tmp_path / "planilha.xlsx"
    doc.write_bytes(bytes(range(256)) * 10)
    html = dashboard.build(cfg, str(doc), out_dir=tmp_path / "saida").read_text(encoding="utf-8")
    assert loader_args(html)[1] == doc.read_bytes()


@pytest.mark.parametrize("name, error", [
    ("relatorio.pdf", "não suportado"),
    ("sem_extensao", "não suportado"),
])
def test_rejects_unsupported_formats(cfg, tmp_path, name, error):
    doc = tmp_path / name
    doc.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        dashboard.build(cfg, str(doc), out_dir=tmp_path / "saida")


def test_rejects_missing_relative_and_huge_files(cfg, tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="não encontrado"):
        dashboard.build(cfg, str(tmp_path / "nao.csv"))
    with pytest.raises(ValueError, match="não encontrado"):
        dashboard.build(cfg, "relativo.csv")
    big = tmp_path / "grande.csv"
    big.write_text("a\n1\n", encoding="utf-8")
    monkeypatch.setattr(dashboard, "MAX_BYTES", 2)
    with pytest.raises(ValueError, match="50 MB"):
        dashboard.build(cfg, str(big))


def test_panel_lookup_falls_back_to_installed_copy(tmp_path, monkeypatch, panel):
    monkeypatch.setattr(dashboard, "installed_panel", lambda: panel)
    assert dashboard.find_panel(Config()) == panel
    assert dashboard.find_panel(Config(painel_dashboard=str(tmp_path / "sumiu.html"))) == panel
    monkeypatch.setattr(dashboard, "installed_panel", lambda: tmp_path / "nada.html")
    with pytest.raises(ValueError, match="não encontrado"):
        dashboard.find_panel(Config())


def test_panel_without_bridge_is_refused(tmp_path):
    old = tmp_path / "antigo.html"
    old.write_text("<html><body></body></html>", encoding="utf-8")
    doc = tmp_path / "d.csv"
    doc.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ponte"):
        dashboard.build(Config(painel_dashboard=str(old)), str(doc), out_dir=tmp_path)


def test_mcp_tool_reports_errors_and_saves(cfg, tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from jarvis import mcp_server

    monkeypatch.setattr("jarvis.config.load", lambda: cfg)
    monkeypatch.setattr(dashboard, "data_dir", lambda: tmp_path)
    opened = []
    monkeypatch.setattr(dashboard, "open_in_browser", opened.append)
    (tmp_path / "x.docx").write_bytes(b"PK")
    assert "não suportado" in mcp_server.criar_dashboard(str(tmp_path / "x.docx"))
    doc = tmp_path / "d.csv"
    doc.write_text("a\n1\n", encoding="utf-8")
    answer = mcp_server.criar_dashboard(str(doc))
    assert "aberto no navegador" in answer and len(opened) == 1 and opened[0].parent == tmp_path / "dashboards"
