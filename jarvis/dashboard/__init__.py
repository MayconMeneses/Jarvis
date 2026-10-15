"""Dashboards de documentos, com o painel do Dashboard Universal embutido na Jarvis.

`painel.html` é uma cópia (versão 0.7.1, arquivo único) do Dashboard Universal do
usuário. A Jarvis não depende do programa instalado: embute o documento escolhido
nessa cópia e chama a ponte do próprio painel (`window.__abrirArquivo(nome, base64)`).
O resultado é um HTML que abre no navegador e roda tudo localmente; o documento nunca
sai do PC.

Para atualizar o painel: troque `painel.html` pelo `dist/index.html` de uma versão
nova (gerado com `npm run build` no projeto do Dashboard Universal) e ajuste
PANEL_VERSION.
"""

from __future__ import annotations

import base64
import json
import re
import time
from pathlib import Path

from jarvis.config import data_dir

PANEL = Path(__file__).with_name("painel.html")
PANEL_VERSION = "0.7.1"
SUPPORTED = (".csv", ".tsv", ".txt", ".xlsx", ".docx", ".pdf", ".json", ".geojson", ".kml", ".kmz")
MAX_BYTES = 50 * 1024 * 1024  # o próprio painel recusa acima disso
BRIDGE = "__abrirArquivo"


def check_document(arquivo: str) -> Path:
    path = Path(str(arquivo).strip().strip('"')).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"arquivo não encontrado: {arquivo}")
    if path.suffix.lower() == ".doc":
        raise ValueError("o formato antigo .doc não é suportado; no Word, use Salvar como → .docx")
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"formato {path.suffix or '(sem extensão)'} não suportado; use CSV, TSV, XLSX, "
                         "DOCX, PDF, JSON, GeoJSON, KML ou KMZ")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("arquivo maior que 50 MB")
    return path


def _js_string(text: str) -> str:
    # dentro de <script>: "</" fecharia a tag
    return json.dumps(text, ensure_ascii=False).replace("</", "<\\/")


def build(arquivo: str, out_dir: Path | None = None, panel: Path = PANEL) -> Path:
    """Gera o HTML do dashboard e devolve o caminho. Só lê o documento; escreve só em out_dir."""
    doc = check_document(arquivo)
    html = panel.read_text(encoding="utf-8")
    end = html.lower().rfind("</body>")
    if BRIDGE not in html or end < 0:
        raise ValueError("o painel embutido não tem a ponte para abrir arquivos")
    data = base64.b64encode(doc.read_bytes()).decode("ascii")
    # Script módulo: roda depois do script do painel (também módulo), quando a ponte já existe.
    loader = f'<script type="module">window.{BRIDGE}({_js_string(doc.name)}, "{data}");</script>\n'
    folder = out_dir or data_dir() / "dashboards"
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w\- ]", "", doc.stem).strip()[:60] or "documento"
    out = folder / f"dashboard {stem} {time.strftime('%Y-%m-%d %H%M%S')}.html"
    out.write_text(html[:end] + loader + html[end:], encoding="utf-8")
    return out


def open_in_browser(path: Path) -> bool:
    import webbrowser

    return webbrowser.open(path.resolve().as_uri())
