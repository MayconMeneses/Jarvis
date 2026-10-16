"""Monta a página da janela a partir de index.html + css/ + js/ (tudo embutido numa string).

A janela recebe o HTML como texto (sem servidor local), então CSS e JavaScript são colados
na ordem abaixo. A ordem importa: é a mesma em que o código foi escrito e testado.
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).parent
CSS = ['base', 'hud', 'buttons', 'chat', 'composer', 'brains', 'review', 'attachments']
JS = ['core', 'render', 'actions', 'review', 'selfupdate', 'messages', 'composer', 'attachments', 'results', 'inputs', 'brains', 'main']


def _join(folder: str, ext: str, names: list[str]) -> str:
    return "\n".join((BASE / folder / f"{name}.{ext}").read_text(encoding="utf-8") for name in names)


def page() -> str:
    html = (BASE / "index.html").read_text(encoding="utf-8")
    html = html.replace("<!--ESTILOS-->", "<style>\n" + _join("css", "css", CSS) + "</style>")
    return html.replace("<!--SCRIPTS-->", "<script>\n" + _join("js", "js", JS) + "</script>")
