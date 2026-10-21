"""Aprendizado de intenções, SEM IA e sem enviar nada a ninguém: um SQLite pequeno em %LOCALAPPDATA%\\SuperJarvis.

Guarda só: frases que a Jarvis não entendeu (com contagem), correções ("Você quis dizer" escolhido), apelidos que o
usuário ensinou (gravados SÓ depois do cartão de aprovação) e contadores por dia. Frases com cara de segredo (e-mail,
link, números longos, tokens) nunca são gravadas. Tamanho limitado; `apagar_tudo()` zera.
"""

from __future__ import annotations

import re
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from jarvis.config import data_dir
from jarvis.local import nlp

MAX_FRASE = 120
MAX_LINHAS = 400   # por tabela: passou disso, as mais antigas saem
MAX_APELIDOS = 100
_SEGREDO = re.compile(r"@|https?://|www\.|\d{5,}|[A-Za-z0-9_\-]{28,}|\b(senha|password|token|chave)\b\s*[:=]", re.I)
SCHEMA = """
CREATE TABLE IF NOT EXISTS falhas (frase TEXT PRIMARY KEY, vezes INTEGER NOT NULL, ultima TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS correcoes (frase TEXT PRIMARY KEY, tipo TEXT NOT NULL, alvo TEXT NOT NULL, rotulo TEXT NOT NULL,
                                      vezes INTEGER NOT NULL, ultima TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS apelidos (frase TEXT PRIMARY KEY, tipo TEXT NOT NULL, alvo TEXT NOT NULL, rotulo TEXT NOT NULL, criado TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dias (dia TEXT PRIMARY KEY, entendidas INTEGER NOT NULL DEFAULT 0, falhas INTEGER NOT NULL DEFAULT 0);
"""


def frase_segura(texto: str) -> str:
    """Frase normalizada e curta, ou "" se não deve ser guardada (vazia, longa demais ou com cara de segredo)."""
    if not isinstance(texto, str) or _SEGREDO.search(texto):
        return ""
    limpa = " ".join(nlp.palavras(texto))
    return limpa if 2 <= len(limpa) <= MAX_FRASE else ""


class Aprendizado:
    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = caminho or data_dir() / "aprendizado.db"

    def _abrir(self) -> sqlite3.Connection:
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.caminho, timeout=5)
        db.executescript(SCHEMA)
        return db

    def _agora(self) -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _podar(self, db: sqlite3.Connection, tabela: str, coluna: str = "ultima") -> None:
        db.execute(f"DELETE FROM {tabela} WHERE rowid IN (SELECT rowid FROM {tabela} ORDER BY {coluna} DESC LIMIT -1 OFFSET ?)", (MAX_LINHAS,))

    # ── contadores ───────────────────────────────────────────────────────
    def contar(self, entendida: bool, dia: date | None = None) -> None:
        coluna = "entendidas" if entendida else "falhas"
        with closing(self._abrir()) as db, db:
            db.execute("INSERT OR IGNORE INTO dias(dia) VALUES (?)", (str(dia or date.today()),))
            db.execute(f"UPDATE dias SET {coluna} = {coluna} + 1 WHERE dia = ?", (str(dia or date.today()),))
            db.execute("DELETE FROM dias WHERE dia < ?", (str(date.today() - timedelta(days=400)),))

    def registrar_falha(self, texto: str) -> None:
        frase = frase_segura(texto)
        if not frase:
            return
        with closing(self._abrir()) as db, db:
            db.execute("INSERT INTO falhas VALUES (?,1,?) ON CONFLICT(frase) DO UPDATE SET vezes = vezes + 1, ultima = excluded.ultima", (frase, self._agora()))
            self._podar(db, "falhas")

    def registrar_correcao(self, texto: str, tipo: str, alvo: str, rotulo: str) -> None:
        frase = frase_segura(texto)
        if not frase or tipo not in ("comando", "conhecimento"):
            return
        with closing(self._abrir()) as db, db:
            db.execute("INSERT INTO correcoes VALUES (?,?,?,?,1,?) ON CONFLICT(frase) DO UPDATE SET tipo = excluded.tipo, alvo = excluded.alvo, "
                       "rotulo = excluded.rotulo, vezes = vezes + 1, ultima = excluded.ultima", (frase, tipo, alvo, rotulo[:80], self._agora()))
            db.execute("DELETE FROM falhas WHERE frase = ?", (frase,))  # virou conhecimento: deixou de ser falha
            self._podar(db, "correcoes")

    # ── apelidos ensinados (só depois do Aprovar) ────────────────────────
    def gravar_apelido(self, frase: str, tipo: str, alvo: str, rotulo: str) -> None:
        limpa = frase_segura(frase)
        if not limpa or tipo not in ("comando", "conhecimento"):
            raise ValueError("frase inválida para apelido")
        with closing(self._abrir()) as db, db:
            if db.execute("SELECT COUNT(*) FROM apelidos").fetchone()[0] >= MAX_APELIDOS and not db.execute(
                    "SELECT 1 FROM apelidos WHERE frase = ?", (limpa,)).fetchone():
                raise ValueError(f"limite de {MAX_APELIDOS} apelidos; apague alguns com \"apague o que você aprendeu sobre como eu falo\"")
            db.execute("INSERT OR REPLACE INTO apelidos VALUES (?,?,?,?,?)", (limpa, tipo, alvo, rotulo[:80], self._agora()))
            db.execute("DELETE FROM falhas WHERE frase = ?", (limpa,))

    def apelido(self, texto: str) -> tuple[str, str, str] | None:
        """(tipo, alvo, rótulo) se a frase é um apelido ensinado ou uma correção já confirmada pelo usuário."""
        frase = frase_segura(texto)
        if not frase:
            return None
        with closing(self._abrir()) as db:
            achou = db.execute("SELECT tipo, alvo, rotulo FROM apelidos WHERE frase = ?", (frase,)).fetchone()
            return achou or db.execute("SELECT tipo, alvo, rotulo FROM correcoes WHERE frase = ?", (frase,)).fetchone()

    def extras_do_casador(self) -> tuple[tuple[str, str, str, str], ...]:
        """Frases confirmadas pelo usuário viram exemplos do casador (quase iguais também passam a casar)."""
        with closing(self._abrir()) as db:
            linhas = db.execute("SELECT tipo, alvo, rotulo, frase FROM apelidos UNION SELECT tipo, alvo, rotulo, frase FROM correcoes").fetchall()
        return tuple(tuple(r) for r in linhas)

    # ── leitura e limpeza ────────────────────────────────────────────────
    def resumo(self, dias: int = 7) -> dict:
        inicio = str(date.today() - timedelta(days=dias - 1))
        with closing(self._abrir()) as db:
            ent, fal = db.execute("SELECT COALESCE(SUM(entendidas),0), COALESCE(SUM(falhas),0) FROM dias WHERE dia >= ?", (inicio,)).fetchone()
            return {
                "entendidas": ent, "falhas": fal, "taxa": round(100 * ent / (ent + fal)) if ent + fal else None,
                "frases_falhas": db.execute("SELECT frase, vezes FROM falhas ORDER BY vezes DESC, ultima DESC LIMIT 5").fetchall(),
                "apelidos": db.execute("SELECT frase, rotulo FROM apelidos ORDER BY criado DESC LIMIT 20").fetchall(),
                "correcoes": db.execute("SELECT frase, rotulo FROM correcoes ORDER BY ultima DESC LIMIT 10").fetchall(),
                "total_aprendido": db.execute("SELECT (SELECT COUNT(*) FROM apelidos) + (SELECT COUNT(*) FROM correcoes)").fetchone()[0],
            }

    def apagar_tudo(self) -> None:
        with closing(self._abrir()) as db, db:
            for tabela in ("falhas", "correcoes", "apelidos", "dias"):
                db.execute(f"DELETE FROM {tabela}")
        with closing(sqlite3.connect(self.caminho)) as db:
            db.execute("VACUUM")
