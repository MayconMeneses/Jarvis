"""Histórico do Radar (radar.db, SQLite): fontes, artigos já vistos e execuções.

Fica em %LOCALAPPDATA%\\SuperJarvis (dados locais e reconstruíveis). Guarda só título, link, data e
fonte: nunca o corpo do artigo. O boletim em si vai para a memória da Jarvis (nota Radar/AAAA-MM-DD).
"""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path

from jarvis.config import data_dir
from jarvis.radar.dedup import id_do_artigo
from jarvis.radar.modelos import Artigo, Fonte

SCHEMA = """
CREATE TABLE IF NOT EXISTS fontes (nome TEXT PRIMARY KEY, feed TEXT NOT NULL, tipo TEXT, idioma TEXT,
  nota REAL, medida INTEGER, ativa INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS artigos (id TEXT PRIMARY KEY, fonte TEXT, titulo TEXT, link TEXT, quando REAL,
  visto REAL, escolhido INTEGER DEFAULT 0);
CREATE VIRTUAL TABLE IF NOT EXISTS titulos USING fts5(titulo, id UNINDEXED, tokenize='unicode61 remove_diacritics 2');
CREATE TABLE IF NOT EXISTS execucoes (id INTEGER PRIMARY KEY AUTOINCREMENT, dia TEXT, inicio REAL, fim REAL,
  varridos INTEGER, novos INTEGER, escolhidos INTEGER, falhas TEXT, resultado TEXT);
"""
RETENCAO_DIAS = 90


class Historico:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or data_dir() / "radar.db"
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.executescript(SCHEMA)

    def fechar(self) -> None:
        with self._lock:
            self._db.close()

    # ── fontes ───────────────────────────────────────────────────────────
    def salvar_fonte(self, f: Fonte) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO fontes (nome, feed, tipo, idioma, nota, medida, ativa) VALUES (?,?,?,?,?,?,?) "
                "ON CONFLICT(nome) DO UPDATE SET feed=excluded.feed, tipo=excluded.tipo, idioma=excluded.idioma, "
                "nota=excluded.nota, medida=excluded.medida, ativa=excluded.ativa",
                (f.nome, f.feed, f.tipo, f.idioma, f.nota, int(f.medida), int(f.ativa)))

    def fontes(self, so_ativas: bool = False) -> list[Fonte]:
        sql = "SELECT * FROM fontes" + (" WHERE ativa=1" if so_ativas else "") + " ORDER BY nota DESC, nome"
        with self._lock:
            linhas = self._db.execute(sql).fetchall()
        return [Fonte(r["nome"], r["feed"], r["tipo"], r["idioma"], r["nota"], bool(r["medida"]), bool(r["ativa"])) for r in linhas]

    def ativar(self, nome: str, ativa: bool) -> bool:
        """Liga/desliga uma fonte sem apagar o histórico dela."""
        with self._lock, self._db:
            return self._db.execute("UPDATE fontes SET ativa=? WHERE lower(nome)=lower(?)", (int(ativa), nome)).rowcount > 0

    # ── artigos ──────────────────────────────────────────────────────────
    def ja_visto(self, artigo: Artigo) -> bool:
        with self._lock:
            return self._db.execute("SELECT 1 FROM artigos WHERE id=?", (id_do_artigo(artigo),)).fetchone() is not None

    def registrar(self, artigos: list[Artigo], escolhidos: set[str] | None = None, agora: float | None = None) -> int:
        """Grava o que foi visto. Devolve quantos eram novos."""
        agora = agora if agora is not None else time.time()
        novos = 0
        with self._lock, self._db:
            for a in artigos:
                ident = id_do_artigo(a)
                existe = self._db.execute("SELECT 1 FROM artigos WHERE id=?", (ident,)).fetchone()
                if existe is None:
                    novos += 1
                    self._db.execute("INSERT INTO artigos (id, fonte, titulo, link, quando, visto) VALUES (?,?,?,?,?,?)",
                                     (ident, a.fonte, a.titulo, a.link, a.quando, agora))
                    self._db.execute("INSERT INTO titulos (titulo, id) VALUES (?,?)", (a.titulo, ident))
                if escolhidos and ident in escolhidos:
                    self._db.execute("UPDATE artigos SET escolhido=1 WHERE id=?", (ident,))
        return novos

    def titulos_recentes(self, dias: int = 14, agora: float | None = None) -> list[str]:
        corte = (agora if agora is not None else time.time()) - dias * 86400
        with self._lock:
            return [r["titulo"] for r in self._db.execute("SELECT titulo FROM artigos WHERE visto>=?", (corte,))]

    def buscar(self, termo: str, limite: int = 10) -> list[dict]:
        consulta = " ".join(f'"{p}"' for p in termo.replace('"', " ").split()[:6])
        if not consulta:
            return []
        with self._lock:
            achados = self._db.execute(
                "SELECT a.titulo, a.link, a.fonte, a.quando FROM titulos t JOIN artigos a ON a.id=t.id "
                "WHERE titulos MATCH ? ORDER BY a.quando DESC LIMIT ?", (consulta, limite)).fetchall()
        return [dict(r) for r in achados]

    def limpar(self, dias: int = RETENCAO_DIAS, agora: float | None = None) -> int:
        corte = (agora if agora is not None else time.time()) - dias * 86400
        with self._lock, self._db:
            ids = [r["id"] for r in self._db.execute("SELECT id FROM artigos WHERE visto<?", (corte,))]
            for ident in ids:
                self._db.execute("DELETE FROM titulos WHERE id=?", (ident,))
            self._db.execute("DELETE FROM artigos WHERE visto<?", (corte,))
            self._db.execute("DELETE FROM execucoes WHERE inicio<?", (corte,))
        return len(ids)

    # ── execuções ────────────────────────────────────────────────────────
    def registrar_execucao(self, dia: str, inicio: float, varridos: int, novos: int, escolhidos: int,
                           falhas: list[str], resultado: str) -> None:
        with self._lock, self._db:
            self._db.execute(
                "INSERT INTO execucoes (dia, inicio, fim, varridos, novos, escolhidos, falhas, resultado) VALUES (?,?,?,?,?,?,?,?)",
                (dia, inicio, time.time(), varridos, novos, escolhidos, "; ".join(falhas)[:1000], resultado))

    def ultima_execucao(self) -> dict | None:
        with self._lock:
            linha = self._db.execute("SELECT * FROM execucoes ORDER BY id DESC LIMIT 1").fetchone()
        return dict(linha) if linha else None
