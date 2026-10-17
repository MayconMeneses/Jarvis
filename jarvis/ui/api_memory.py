"""Janela "◈ Memória": listar, buscar, editar, apagar e exportar o que a Jarvis guardou."""

from __future__ import annotations

import sqlite3

import webview

from jarvis import memory_obsidian


def _caminho(escolha) -> str:
    """O seletor de arquivos devolve um texto ou uma lista, conforme a versão do pywebview."""
    return escolha if isinstance(escolha, str) else escolha[0]


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

    def memory_backup(self, password: str) -> dict:
        """Cópia CRIPTOGRAFADA da memória (abre também no celular). A senha não é guardada nem vai para o diário."""
        from jarvis import backup

        if self._window is None:
            return {"error": "janela indisponível"}
        if len(str(password)) < backup.MIN_SENHA:
            return {"error": f"Digite uma senha de pelo menos {backup.MIN_SENHA} caracteres no campo ao lado."}
        local = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename="jarvis-copia.jarvis-backup")
        if not local:
            return {"cancelado": True}
        try:
            count = backup.exportar_arquivo(self._memory, _caminho(local), str(password))
        except (OSError, ValueError, sqlite3.Error) as exc:
            return {"error": f"Não foi possível gravar a cópia: {exc}"}
        self._diary("Cópia segura da memória gravada")
        return {"text": f"{count} nota(s) gravadas com criptografia. Guarde a senha: sem ela a cópia não abre."}

    def memory_restore(self, password: str) -> dict:
        from jarvis import backup

        if self._window is None:
            return {"error": "janela indisponível"}
        escolha = self._window.create_file_dialog(webview.FileDialog.OPEN)
        if not escolha:
            return {"cancelado": True}
        try:
            novas, atualizadas = backup.importar_arquivo(self._memory, _caminho(escolha), str(password))
        except (OSError, ValueError, sqlite3.Error) as exc:
            return {"error": f"Não consegui restaurar: {exc}"}
        self._diary("Cópia da memória restaurada")
        return {"text": f"Restauradas: {novas} nota(s) nova(s) e {atualizadas} atualizada(s) (a versão mais recente de cada nota vence)."}

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
