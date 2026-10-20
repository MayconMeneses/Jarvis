"""Monta a página da janela a partir de index.html + css/ + js/ (tudo embutido numa string).

A janela recebe o HTML como texto (sem servidor local), então CSS e JavaScript são colados
na ordem abaixo. A ordem importa: é a mesma em que o código foi escrito e testado.
"""

from __future__ import annotations

from pathlib import Path

BASE = Path(__file__).parent
CSS = ['base', 'hud', 'buttons', 'chat', 'composer', 'brains', 'review', 'attachments', 'memory', 'memory-grafo', 'oficina', 'uso', 'agents', 'face', 'design']
JS = ['core', 'render', 'actions', 'review', 'selfupdate', 'update', 'messages', 'composer', 'attachments', 'orbe-estado', 'orbe', 'results', 'inputs', 'brains', 'memory-grafo', 'memory', 'mobile', 'oficina', 'uso-graficos', 'uso', 'uso-config', 'agents-estado', 'agents-desenho', 'agents', 'agenda-email', 'tema', 'face-paineis', 'face', 'main']


def _join(folder: str, ext: str, names: list[str]) -> str:
    return "\n".join((BASE / folder / f"{name}.{ext}").read_text(encoding="utf-8") for name in names)


def page(cfg=None) -> str:
    """HTML da janela. Com a configuração, já sai com o tema e os efeitos certos no <html> (sem piscar o tema errado)."""
    from jarvis.ui.api_tema import efeitos_validos, tema_valido  # import tardio: api_tema usa jarvis.config

    html = (BASE / "index.html").read_text(encoding="utf-8")
    tema, efeitos = tema_valido(getattr(cfg, "tema", "hud")), efeitos_validos(getattr(cfg, "efeitos_visuais", "completo"))
    html = html.replace('<html lang="pt-BR">', f'<html lang="pt-BR" data-tema="{tema}" data-efeitos="{efeitos}">', 1)
    html = html.replace("<!--ESTILOS-->", "<style>\n" + _join("css", "css", CSS) + "</style>")
    html = html.replace("<!--SCRIPTS-->", (BASE / "uso.html").read_text(encoding="utf-8") + "<!--SCRIPTS-->")  # diálogo "Uso de IA"
    for dialogo in ("agents", "agenda-email"):  # painel de agentes e "Agenda e e-mail"
        html = html.replace("<!--SCRIPTS-->", (BASE / f"{dialogo}.html").read_text(encoding="utf-8") + "<!--SCRIPTS-->")
    html = html.replace("<!--SCRIPTS-->", (BASE / "face.html").read_text(encoding="utf-8") + "<!--SCRIPTS-->")  # tela FACE
    return html.replace("<!--SCRIPTS-->", "<script>\n" + _join("js", "js", JS) + "</script>")
