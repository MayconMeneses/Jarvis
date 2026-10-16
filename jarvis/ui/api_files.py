"""Arquivos: anexos (clipe e arrastar) e dashboard de documentos."""

from __future__ import annotations

from pathlib import Path

import webview


class FilesMixin:
    """Anexos e dashboards: o que a janela faz com arquivos do usuário."""

    def pick_files(self) -> dict:
        """Abre o seletor de arquivos do Windows e guarda cópias dos escolhidos."""
        dialog = getattr(getattr(webview, "FileDialog", None), "OPEN", None) or webview.OPEN_DIALOG
        chosen = self._window.create_file_dialog(dialog, allow_multiple=True) if self._window else None
        return self._store_many([("path", p) for p in (chosen or [])])

    def attach_data(self, name: str, b64: str) -> dict:
        """Arquivo arrastado para a janela (o navegador entrega o conteúdo, não o caminho)."""
        import base64

        try:
            data = base64.b64decode(str(b64), validate=True)
        except ValueError:
            return {"anexos": [], "erros": [f"{name}: conteúdo inválido"]}
        return self._store_many([("data", (str(name), data))])

    def _store_many(self, items) -> dict:
        added, errors = [], []
        for kind, value in items:
            try:
                att = self._files.add_path(value) if kind == "path" else self._files.add(*value)
                added.append(att.public())
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        return {"anexos": added, "erros": errors}

    def dashboard(self) -> dict:
        """Botão 📊: escolhe um documento e abre o dashboard dele no navegador."""
        from jarvis import dashboard

        if self._window is None:
            return {"error": "janela indisponível"}
        tipos = ("Dados (" + ";".join("*" + e for e in dashboard.SUPPORTED) + ")", "Todos os arquivos (*.*)")
        escolha = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=tipos)
        if not escolha:
            return {"cancelado": True}
        try:
            path = dashboard.build(escolha[0])
        except (ValueError, OSError) as exc:
            return {"error": f"Não foi possível criar o dashboard: {exc}"}
        dashboard.open_in_browser(path)
        self._diary(f"Dashboard criado de {Path(escolha[0]).name}")
        self._conversation.note(f"Criei um dashboard do arquivo {escolha[0]} e abri no navegador ({path}).")
        return {"text": f"📊 Abri no navegador o dashboard de {Path(escolha[0]).name}. "
                        f"Ele fica salvo em {path}."}
