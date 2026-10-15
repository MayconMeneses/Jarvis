"""Dashboards de documentos usando o Dashboard Universal do usuário.

A Jarvis não refaz os gráficos: pega o painel do usuário (um único HTML), embute o
arquivo escolhido e chama a mesma ponte que o programa de desktop usa
(`window.__abrirArquivo(nome, base64)`). O resultado é um HTML que abre no navegador
e roda tudo localmente; o documento nunca sai do PC.

Ordem para achar o painel: `painel_dashboard` no config.json, depois a cópia que o
programa instalado mantém atualizada pelo GitHub.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

from jarvis.config import Config, data_dir

SUPPORTED = (".csv", ".tsv", ".txt", ".xlsx", ".json", ".geojson", ".kml", ".kmz")
MAX_BYTES = 50 * 1024 * 1024  # o próprio painel recusa acima disso
BRIDGE = "__abrirArquivo"


def installed_panel() -> Path:
    return Path(os.environ.get("APPDATA", Path.home())) / "dashboard-universal-desktop" / "painel" / "index.html"


def find_panel(cfg: Config) -> Path:
    candidates = [Path(cfg.painel_dashboard)] if cfg.painel_dashboard else []
    candidates.append(installed_panel())
    for path in candidates:
        if path.is_file():
            return path
    raise ValueError("painel do Dashboard Universal não encontrado: instale o programa ou informe "
                     "o caminho do index.html em painel_dashboard no config.json")


def check_document(arquivo: str) -> Path:
    path = Path(str(arquivo).strip().strip('"')).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise ValueError(f"arquivo não encontrado: {arquivo}")
    if path.suffix.lower() not in SUPPORTED:
        raise ValueError(f"formato {path.suffix or '(sem extensão)'} não suportado; use CSV, TSV, XLSX, "
                         "JSON, GeoJSON, KML ou KMZ")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("arquivo maior que 50 MB")
    return path


def _js_string(text: str) -> str:
    # dentro de <script>: "</" fecharia a tag
    return json.dumps(text, ensure_ascii=False).replace("</", "<\\/")


def build(cfg: Config, arquivo: str, out_dir: Path | None = None) -> Path:
    """Gera o HTML do dashboard e devolve o caminho. Só lê o documento; escreve só em out_dir."""
    doc = check_document(arquivo)
    panel = find_panel(cfg).read_text(encoding="utf-8")
    end = panel.lower().rfind("</body>")
    if BRIDGE not in panel or end < 0:
        raise ValueError("este painel não tem a ponte para abrir arquivos; atualize o Dashboard Universal")
    data = base64.b64encode(doc.read_bytes()).decode("ascii")
    # Script módulo: roda depois do script do painel (também módulo), quando a ponte já existe.
    loader = f'<script type="module">window.{BRIDGE}({_js_string(doc.name)}, "{data}");</script>\n'
    folder = out_dir or data_dir() / "dashboards"
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^\w\- ]", "", doc.stem).strip()[:60] or "documento"
    out = folder / f"dashboard {stem} {time.strftime('%Y-%m-%d %H%M%S')}.html"
    out.write_text(panel[:end] + loader + panel[end:], encoding="utf-8")
    return out


def open_in_browser(path: Path) -> bool:
    import webbrowser

    return webbrowser.open(path.resolve().as_uri())
