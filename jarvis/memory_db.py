"""Memória própria da Jarvis: um único arquivo SQLite, sem depender do Obsidian.

    %APPDATA%\\SuperJarvis\\memoria.db

Tudo é uma "nota" com uma referência em forma de caminho (`ref`), por exemplo:

    Memória/Preferência de vagas     um fato durável por nota
    Diário/2026-10-15                linhas com hora do que foi pedido e feito
    Relatórios/2026-10-15 Briefing   briefings e resumos
    Projetos/<projeto>/Sobre         ficha do projeto (descrição, stack, decisões...)
    Projetos/<projeto>/<data> Plano  resultados das tarefas do Claude Code
    Pesquisas/<data> <tema>          pesquisas na internet
    Perfil Profissional              perfil usado na busca de vagas

A busca usa FTS5 (rápida e leve) e ignora acentos e maiúsculas. Cada chamada abre e
fecha a própria conexão, então a janela, a fila de tarefas e o servidor MCP (outro
processo) podem usar o mesmo arquivo ao mesmo tempo (modo WAL).

O Obsidian virou opcional (importar/exportar: jarvis/memory_obsidian.py). O banco é sempre a
fonte da verdade.
"""

from __future__ import annotations

import re
import sqlite3
import time
import unicodedata
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from jarvis import config

DB_NAME = "memoria.db"
MEMORY_PREFIX = "Memória/"
INDEX_NAME = "00 - Índice"
MAX_INDEX_CHARS = 2500
MAX_BODY = 200_000
_FORBIDDEN = re.compile(r'[\\/:*?"<>|#^\[\]]')

SCHEMA = """
CREATE TABLE IF NOT EXISTS notas (
    ref TEXT PRIMARY KEY, tipo TEXT NOT NULL DEFAULT 'nota', titulo TEXT NOT NULL,
    corpo TEXT NOT NULL DEFAULT '', resumo TEXT NOT NULL DEFAULT '',
    criado TEXT NOT NULL, atualizado TEXT NOT NULL
);
CREATE VIRTUAL TABLE IF NOT EXISTS notas_fts USING fts5(
    ref UNINDEXED, titulo, corpo, tokenize = 'unicode61 remove_diacritics 2'
);
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def clean_title(title: str) -> str:
    return _FORBIDDEN.sub("", title).strip()[:80]


def clean_ref(ref: str) -> str:
    """Caminho de nota seguro: sem "..", sem caracteres proibidos, com "/" como separador."""
    parts = [_FORBIDDEN.sub("", p).strip().strip(".") for p in re.split(r"[\\/]", str(ref))]
    cleaned = "/".join(p[:120] for p in parts if p)
    if not cleaned:
        raise ValueError("referência da nota vazia")
    return cleaned[:240]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def db_path(cfg: config.Config | None = None) -> Path:
    if cfg is not None and cfg.memoria_db:
        return Path(cfg.memoria_db)
    return config.config_dir() / DB_NAME


class MemoryDB:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)  # fora de _tx: executescript confirma a transação aberta
        finally:
            db.close()

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=NORMAL")  # seguro em WAL; evita um fsync por gravação
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
            except BaseException:
                db.execute("ROLLBACK")
                raise
            db.execute("COMMIT")
        finally:
            db.close()

    # ── notas genéricas ──────────────────────────────────────────────────
    def put(self, ref: str, body: str, tipo: str = "nota", resumo: str = "", title: str = "",
            created: str = "", updated: str = "") -> str:
        """Cria ou substitui a nota; mantém a data de criação da anterior."""
        ref = clean_ref(ref)
        title = title or ref.rsplit("/", 1)[-1]
        with self._tx() as db:
            self._write(db, ref, tipo, title, body[:MAX_BODY], resumo[:140], created, updated)
        return ref

    def _write(self, db, ref, tipo, title, body, resumo, created="", updated="") -> None:
        now = _now()
        old = db.execute("SELECT criado FROM notas WHERE ref = ?", (ref,)).fetchone()
        db.execute(
            "INSERT OR REPLACE INTO notas (ref, tipo, titulo, corpo, resumo, criado, atualizado) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (ref, tipo, title, body, resumo, old["criado"] if old else (created or now), updated or now),
        )
        db.execute("DELETE FROM notas_fts WHERE ref = ?", (ref,))
        db.execute("INSERT INTO notas_fts (ref, titulo, corpo) VALUES (?, ?, ?)", (ref, title, body))

    def get(self, ref: str) -> str | None:
        with self._tx() as db:
            row = db.execute("SELECT corpo FROM notas WHERE ref = ?", (clean_ref(ref),)).fetchone()
        return row["corpo"] if row else None

    def edit(self, ref: str, body: str) -> None:
        """Troca o texto de uma nota que já existe, mantendo tipo, título e data de criação (usado na janela)."""
        ref = clean_ref(ref)
        body = body.strip("\n")[:MAX_BODY]
        with self._tx() as db:
            row = db.execute("SELECT tipo, titulo, resumo FROM notas WHERE ref = ?", (ref,)).fetchone()
            if row is None:
                raise ValueError("nota não encontrada")
            resumo = row["resumo"]
            if row["tipo"] == "memoria":  # o resumo acompanha a primeira linha editada
                resumo = next((l.strip() for l in body.splitlines() if l.strip()), "")[:140]
            self._write(db, ref, row["tipo"], row["titulo"], body, resumo)

    def exists(self, ref: str) -> bool:
        return self.get(ref) is not None

    def delete(self, ref: str) -> bool:
        ref = clean_ref(ref)
        with self._tx() as db:
            db.execute("DELETE FROM notas_fts WHERE ref = ?", (ref,))
            return db.execute("DELETE FROM notas WHERE ref = ?", (ref,)).rowcount > 0

    def append(self, ref: str, line: str, header: str = "", tipo: str = "nota") -> str:
        """Acrescenta uma linha (cria a nota com `header` se for nova), sem corrida entre processos."""
        ref = clean_ref(ref)
        with self._tx() as db:
            row = db.execute("SELECT corpo FROM notas WHERE ref = ?", (ref,)).fetchone()
            body = (row["corpo"] if row else header) + line.rstrip("\n") + "\n"
            self._write(db, ref, tipo, ref.rsplit("/", 1)[-1], body[:MAX_BODY], "")
        return ref

    def list_notes(self, prefix: str = "", limit: int = 500) -> list[dict]:
        like = prefix.replace("%", "").replace("_", "") + "%"
        with self._tx() as db:
            rows = db.execute(
                "SELECT ref, tipo, resumo, criado, atualizado FROM notas WHERE ref LIKE ? "
                "ORDER BY atualizado DESC, ref LIMIT ?", (like, limit)).fetchall()
        return [dict(r) for r in rows]

    def count(self) -> int:
        with self._tx() as db:
            return db.execute("SELECT COUNT(*) FROM notas").fetchone()[0]

    # ── memória durável (mesma interface da Vault do Obsidian) ───────────
    def remember(self, title: str, fact: str, summary: str = "") -> str:
        title, fact = clean_title(title), fact.strip()
        if not title or not fact:
            raise ValueError("título e fato são obrigatórios")
        summary = (summary or fact.splitlines()[0])[:140].replace("\n", " ")
        return self.put(MEMORY_PREFIX + title, fact, "memoria", summary, title)

    def memories(self) -> list[tuple[str, str]]:
        with self._tx() as db:
            rows = db.execute("SELECT titulo, resumo, corpo FROM notas WHERE ref LIKE ?",
                              (MEMORY_PREFIX + "%",)).fetchall()
        found = []
        for r in rows:
            first = next((l.strip() for l in r["corpo"].splitlines() if l.strip()), "")
            found.append((r["titulo"], r["resumo"] or first[:140]))
        return sorted(found)

    def index_text(self) -> str:
        text = "\n".join(f"- {title}: {summary}" for title, summary in self.memories())
        return text[:MAX_INDEX_CHARS] + ("\n- (mais memórias guardadas)" if len(text) > MAX_INDEX_CHARS else "")

    def search(self, query: str, limit: int = 8) -> list[dict]:
        terms = [re.sub(r"\W", "", t) for t in _fold(query).split()]
        terms = [t for t in terms if len(t) > 2]
        if not terms:
            return []
        match = " OR ".join(f'"{t}"*' for t in terms)
        with self._tx() as db:
            rows = db.execute(
                "SELECT ref, snippet(notas_fts, 2, '', '', '…', 32) AS trecho FROM notas_fts "
                "WHERE notas_fts MATCH ? ORDER BY bm25(notas_fts, 1.0, 5.0, 1.0) LIMIT ?",
                (match, limit)).fetchall()
        return [{"nota": r["ref"], "trecho": r["trecho"].replace("\n", " ")} for r in rows]

    def read(self, ref: str, max_chars: int = 8000) -> str:
        body = self.get(ref)
        if body is None:
            raise ValueError("nota não encontrada")
        return body[:max_chars]

    # ── diário e relatórios ──────────────────────────────────────────────
    def diary(self, entry: str) -> None:
        today = date.today()
        line = entry.strip().replace("\n", " ")[:300]
        self.append(f"Diário/{today.isoformat()}", f"- {datetime.now():%H:%M} — {line}",
                    header=f"# Diário {today:%d/%m/%Y}\n\n", tipo="diario")

    def save_report(self, name: str, content: str, folder: str = "Relatórios") -> str:
        name = clean_title(name)
        if not name:
            raise ValueError("informe um nome para o relatório")
        return self.put(f"{folder}/{date.today().isoformat()} {name}", content, "relatorio", title=name)

    # ── metadados ────────────────────────────────────────────────────────
    def meta(self, key: str) -> str | None:
        with self._tx() as db:
            row = db.execute("SELECT valor FROM meta WHERE chave = ?", (key,)).fetchone()
        return row["valor"] if row else None

    def set_meta(self, key: str, value: str) -> None:
        with self._tx() as db:
            db.execute("INSERT OR REPLACE INTO meta (chave, valor) VALUES (?, ?)", (key, value))


def open_memory(cfg: config.Config | None = None) -> MemoryDB:
    """Abre (criando, se preciso) a memória da Jarvis. Na primeira vez, importa o Jarvis/ do Obsidian, se houver."""
    from jarvis.memory_obsidian import import_obsidian

    created = not db_path(cfg).exists()
    db = MemoryDB(db_path(cfg))
    if created and cfg is not None and cfg.obsidian_vault and db.meta("importado_obsidian") is None:
        try:
            count = import_obsidian(db, cfg.obsidian_vault)
        except OSError:
            count = 0
        db.set_meta("importado_obsidian", f"{time.strftime('%Y-%m-%d %H:%M')} ({count} notas)")
    return db
