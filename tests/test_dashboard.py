import base64
import json
import re

import pytest

from jarvis import dashboard

PANEL = ('<!doctype html><html><head><script type="module">window.__abrirArquivo = () => {};</script>'
         '</head><body><main id="app"></main></body></html>')


@pytest.fixture
def panel(tmp_path):
    path = tmp_path / "painel.html"
    path.write_text(PANEL, encoding="utf-8")
    return path


def loader_args(html: str) -> tuple[str, bytes]:
    m = re.search(r'<script type="module">window\.__abrirArquivo\((.*?), "([A-Za-z0-9+/=]*)"\);</script>', html)
    assert m, "script de carga não encontrado"
    return json.loads(m.group(1).replace("<\\/", "</")), base64.b64decode(m.group(2))


needs_panel = pytest.mark.skipif(not dashboard.PANEL.is_file(), reason="painel.html (build gerado) não está no repositório")


@needs_panel
def test_bundled_panel_is_inside_jarvis_and_has_the_bridge():
    assert dashboard.PANEL.parent == dashboard.PANEL.parent.parent / "dashboard"
    html = dashboard.PANEL.read_text(encoding="utf-8")
    assert "window.__abrirArquivo" in html and "</body>" in html.lower()


@needs_panel
def test_build_uses_the_bundled_panel_by_default(tmp_path):
    doc = tmp_path / "vendas.csv"
    doc.write_text("mes;total\njan;10\n", encoding="utf-8")
    html = dashboard.build(str(doc), out_dir=tmp_path / "saida").read_text(encoding="utf-8")
    assert "Dashboard Universal" in html and loader_args(html)[0] == "vendas.csv"


def test_build_embeds_the_document_after_the_panel_script(panel, tmp_path):
    doc = tmp_path / "vendas.csv"
    doc.write_bytes("mês;total\njan;10\n".encode("utf-8"))
    out = dashboard.build(str(doc), out_dir=tmp_path / "saida", panel=panel)
    html = out.read_text(encoding="utf-8")
    assert out.parent == tmp_path / "saida" and out.suffix == ".html" and "vendas" in out.name
    assert html.index("window.__abrirArquivo = ") < html.index("window.__abrirArquivo(") < html.index("</body>")
    assert loader_args(html) == ("vendas.csv", doc.read_bytes())
    assert doc.read_bytes() == "mês;total\njan;10\n".encode("utf-8")  # documento intacto


def test_file_name_cannot_close_the_script_tag():
    escaped = dashboard._js_string('a</script><b>.json')
    assert "</" not in escaped and json.loads(escaped.replace("<\\/", "</")) == "a</script><b>.json"


@pytest.mark.parametrize("name", ["planilha.xlsx", "relatorio.pdf", "contrato.docx"])
def test_binary_formats_round_trip(panel, tmp_path, name):
    doc = tmp_path / name
    doc.write_bytes(bytes(range(256)) * 10)
    html = dashboard.build(str(doc), out_dir=tmp_path / "saida", panel=panel).read_text(encoding="utf-8")
    assert loader_args(html)[1] == doc.read_bytes()


@pytest.mark.parametrize("name, error", [
    ("antigo.doc", "Salvar como"),
    ("foto.png", "não suportado"),
    ("sem_extensao", "não suportado"),
])
def test_rejects_unsupported_formats(panel, tmp_path, name, error):
    doc = tmp_path / name
    doc.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        dashboard.build(str(doc), out_dir=tmp_path / "saida", panel=panel)


def test_rejects_missing_relative_and_huge_files(panel, tmp_path, monkeypatch):
    with pytest.raises(ValueError, match="não encontrado"):
        dashboard.build(str(tmp_path / "nao.csv"), panel=panel)
    with pytest.raises(ValueError, match="não encontrado"):
        dashboard.build("relativo.csv", panel=panel)
    big = tmp_path / "grande.csv"
    big.write_text("a\n1\n", encoding="utf-8")
    monkeypatch.setattr(dashboard, "MAX_BYTES", 2)
    with pytest.raises(ValueError, match="50 MB"):
        dashboard.build(str(big), panel=panel)


def test_panel_without_bridge_is_refused(tmp_path):
    old = tmp_path / "antigo.html"
    old.write_text("<html><body></body></html>", encoding="utf-8")
    doc = tmp_path / "d.csv"
    doc.write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="ponte"):
        dashboard.build(str(doc), out_dir=tmp_path, panel=old)


def test_mcp_tool_reports_errors_and_saves(tmp_path, monkeypatch):
    pytest.importorskip("mcp")
    from jarvis.mcp_tools import document_tools as mcp_server

    monkeypatch.setattr(dashboard, "data_dir", lambda: tmp_path)
    opened = []
    monkeypatch.setattr(dashboard, "open_in_browser", opened.append)
    (tmp_path / "x.doc").write_bytes(b"x")
    assert "Salvar como" in mcp_server.criar_dashboard(str(tmp_path / "x.doc"))
    doc = tmp_path / "d.csv"
    doc.write_text("a\n1\n", encoding="utf-8")
    answer = mcp_server.criar_dashboard(str(doc))
    assert "aberto no navegador" in answer and len(opened) == 1 and opened[0].parent == tmp_path / "dashboards"


def test_missing_panel_gives_a_clear_message(tmp_path):
    doc = tmp_path / "dados.csv"
    doc.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="painel do dashboard não está instalado"):
        dashboard.build(str(doc), out_dir=tmp_path / "saida", panel=tmp_path / "nao-existe.html")
