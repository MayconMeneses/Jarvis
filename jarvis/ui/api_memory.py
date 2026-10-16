"""Janela "◈ Memória": listar, buscar, editar, apagar e exportar o que a Jarvis guardou."""

from __future__ import annotations

import sqlite3

import webview

from jarvis import memory_obsidian


class MemoryMixin:
    """Visualizador da memória própria da Jarvis (SQLite); nada depende do Obsidian."""

    def memory_list(self, query: str = "") -> dict:
        """Notas mais recentes ou o resultado de uma busca."""
        try:
            if str(query).strip():
                notes = [{"ref": h["nota"], "resumo": h["trecho"]} for h in self._memory.search(str(query), 40)]
            else:
                notes = [{"ref": n["ref"], "resumo": n["resumo"], "atualizado": n["atualizado"][:10]}
                         for n in self._memory.list_notes(limit=200)]
            return {"notas": notes, "total": self._memory.count()}
        except sqlite3.Error as exc:
            return {"error": f"Não foi possível ler a memória: {exc}"}

    def memory_get(self, ref: str) -> dict:
        try:
            return {"ref": str(ref), "texto": self._memory.read(str(ref), 200_000)}
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}

    def memory_save(self, ref: str, text: str) -> dict:
        try:
            self._memory.edit(str(ref), str(text))
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        self._diary(f"Memória editada na janela: {ref}")
        return {"ok": True}

    def memory_delete(self, ref: str) -> dict:
        try:
            ok = self._memory.delete(str(ref))
        except (ValueError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        self._diary(f"Memória apagada na janela: {ref}")
        return {"ok": ok}

    def memory_export(self) -> dict:
        """Grava uma cópia em Markdown numa pasta escolhida (por exemplo, a Jarvis/ de um cofre do Obsidian)."""
        if self._window is None:
            return {"error": "janela indisponível"}
        chosen = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        if not chosen:
            return {"cancelado": True}
        try:
            count = memory_obsidian.export_markdown(self._memory, chosen[0])
        except (OSError, sqlite3.Error) as exc:
            return {"error": f"Não foi possível exportar: {exc}"}
        return {"text": f"{count} nota(s) gravadas em {chosen[0]}."}
