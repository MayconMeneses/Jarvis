"""Pareamento de aparelhos: código de 6 dígitos de uso único → token por aparelho (só o hash fica no disco)."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path

from jarvis.config import data_dir

VALIDADE_CODIGO = 300      # segundos
MAX_ERROS = 5
BLOQUEIO = 300             # segundos de bloqueio depois de errar o código várias vezes


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class Pareamento:
    def __init__(self, arquivo: Path | None = None, relogio=time.time) -> None:
        self.arquivo = arquivo or data_dir() / "celulares.json"
        self._agora = relogio
        self._codigo = ""
        self._expira = 0.0
        self._erros = 0
        self._bloqueado_ate = 0.0

    # ── código de uso único ──────────────────────────────────────────────
    def novo_codigo(self) -> str:
        self._codigo, self._expira, self._erros = f"{secrets.randbelow(10**6):06d}", self._agora() + VALIDADE_CODIGO, 0
        return self._codigo

    def trocar(self, codigo: str, nome: str) -> str | None:
        """Token novo se o código estiver certo e válido; None se não. Erros demais bloqueiam por alguns minutos."""
        agora = self._agora()
        if agora < self._bloqueado_ate:
            return None
        if not self._codigo or agora > self._expira or not hmac.compare_digest(str(codigo).strip(), self._codigo):
            self._erros += 1
            if self._erros >= MAX_ERROS:
                self._codigo, self._bloqueado_ate = "", agora + BLOQUEIO
            return None
        self._codigo = ""  # uso único
        token = secrets.token_urlsafe(32)
        aparelhos = self._ler()
        aparelhos.append({"id": secrets.token_hex(4), "nome": (nome or "celular").strip()[:40], "hash": _hash(token), "criado": int(agora)})
        self._gravar(aparelhos)
        return token

    # ── tokens ───────────────────────────────────────────────────────────
    def validar(self, token: str) -> dict | None:
        alvo = _hash(token or "")
        for aparelho in self._ler():
            if hmac.compare_digest(aparelho["hash"], alvo):
                return {"id": aparelho["id"], "nome": aparelho["nome"]}
        return None

    def listar(self) -> list[dict]:
        return [{"id": a["id"], "nome": a["nome"], "criado": a["criado"]} for a in self._ler()]

    def revogar(self, id_: str) -> bool:
        restantes = [a for a in self._ler() if a["id"] != id_]
        mudou = len(restantes) != len(self._ler())
        if mudou:
            self._gravar(restantes)
        return mudou

    def _ler(self) -> list[dict]:
        try:
            return json.loads(self.arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def _gravar(self, aparelhos: list[dict]) -> None:
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.arquivo.write_text(json.dumps(aparelhos, indent=1), encoding="utf-8")
