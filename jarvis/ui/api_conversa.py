"""Ponte da conversa: perfil do usuário (ver, mudar, apagar com cartão) e fatos duráveis que viram propostas de memória."""

from __future__ import annotations

import logging
import sqlite3

log = logging.getLogger(__name__)


class ConversaMixin:
    def perfil_usuario(self) -> dict:
        """O que a Jarvis sabe sobre o usuário (campos definidos por ele e deduzidos das notas)."""
        from jarvis.conversa import perfil

        try:
            return {"campos": {c: {"nome": perfil.CAMPOS[c], "valor": v, "origem": o}
                               for c, (v, o) in perfil.compilar(self._memory, self._cfg).items()}}
        except (sqlite3.Error, OSError) as exc:
            return {"error": f"Não foi possível ler o perfil: {exc}"}

    def perfil_definir(self, campo: str, valor: str) -> dict:
        """Cria o cartão 'Atualizar seu perfil?'. Só grava depois do Aprovar."""
        from jarvis.conversa import perfil

        try:
            acao = perfil.propor(self._store, self._memory, str(campo), str(valor))
        except (ValueError, OSError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        return {"actions": [{"id": acao.id, "descricao": acao.descricao, "motivo": acao.motivo}]}

    def perfil_apagar(self, campo: str) -> dict:
        from jarvis.conversa import perfil

        try:
            acao = perfil.propor_apagar(self._store, self._memory, str(campo))
        except (ValueError, OSError, sqlite3.Error) as exc:
            return {"error": str(exc)}
        return {"actions": [{"id": acao.id, "descricao": acao.descricao, "motivo": acao.motivo}]}

    def _fatos_da_conversa(self, pedido: str) -> None:
        """Fato durável que o usuário contou vira cartão de memória viva (nunca grava sozinho)."""
        from jarvis.conversa import fatos

        try:
            fatos.propor(self._store, self._memory, pedido, "conversa")
        except (ValueError, OSError, sqlite3.Error):
            log.info("não foi possível propor a lembrança da conversa", exc_info=True)
