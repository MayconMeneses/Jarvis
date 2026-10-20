"""Registro do uso de IA em SQLite (uso_ia.db, na pasta de dados). Só números e rótulos, nunca conteúdo.

Cada linha é uma chamada de IA (fonte "ao_vivo", gravada pelo roteador) ou uma resposta do Claude Code
lida dos arquivos da própria ferramenta (fonte "jsonl"). Linhas com a mesma `chave` (mensagem + pedido)
são a mesma resposta repetida: fica a de maior saída.
"""

from __future__ import annotations

import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path

from jarvis.config import data_dir
from jarvis.uso import precos

GRATIS = {"gemini", "nvidia", "local", "llm"}  # sem custo por token (cota/limites à parte)
COLUNAS = ("ts", "dia", "fonte", "provedor", "modelo", "projeto", "sessao", "sub", "tin", "tout", "cw", "cw1h", "cr", "custo_rep")
ESQUEMA = """
CREATE TABLE IF NOT EXISTS uso (
  id INTEGER PRIMARY KEY AUTOINCREMENT, chave TEXT UNIQUE, ts REAL NOT NULL, dia TEXT NOT NULL,
  fonte TEXT NOT NULL, provedor TEXT NOT NULL, modelo TEXT NOT NULL DEFAULT '', projeto TEXT NOT NULL DEFAULT '',
  sessao TEXT NOT NULL DEFAULT '', sub INTEGER NOT NULL DEFAULT 0,
  tin INTEGER NOT NULL DEFAULT 0, tout INTEGER NOT NULL DEFAULT 0, cw INTEGER NOT NULL DEFAULT 0,
  cw1h INTEGER NOT NULL DEFAULT 0, cr INTEGER NOT NULL DEFAULT 0, custo_rep REAL);
CREATE INDEX IF NOT EXISTS uso_dia ON uso(dia);
CREATE INDEX IF NOT EXISTS uso_ts ON uso(ts);
CREATE INDEX IF NOT EXISTS uso_sessao ON uso(sessao);
CREATE TABLE IF NOT EXISTS coleta (arquivo TEXT PRIMARY KEY, posicao INTEGER NOT NULL, mtime REAL NOT NULL);
CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT NOT NULL);
"""


def caminho_padrao() -> Path:
    return data_dir() / "uso_ia.db"


class Registro:
    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = caminho or caminho_padrao()
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        self._trava = threading.RLock()
        self._db = sqlite3.connect(self.caminho, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.executescript(ESQUEMA)

    def fechar(self) -> None:
        with self._trava:
            self._db.close()

    # ── escrita ──────────────────────────────────────────────────────────
    @staticmethod
    def _tupla(*, ts: float, fonte: str, provedor: str, modelo: str = "", projeto: str = "", sessao: str = "",
               sub: bool = False, uso: dict | None = None, custo_rep: float | None = None, chave: str | None = None) -> tuple:
        u = uso or {}
        return (chave, ts, datetime.fromtimestamp(ts).strftime("%Y-%m-%d"), fonte, provedor, modelo, projeto, sessao, int(bool(sub)),
                int(u.get("in", 0)), int(u.get("out", 0)), int(u.get("cw", 0)), int(u.get("cw1h", 0)), int(u.get("cr", 0)), custo_rep)

    def inserir(self, **campos) -> None:
        with self._trava, self._db:
            self._gravar(self._tupla(**campos))

    def _gravar(self, linha: tuple) -> None:
        self._db.execute(
            "INSERT INTO uso(chave,ts,dia,fonte,provedor,modelo,projeto,sessao,sub,tin,tout,cw,cw1h,cr,custo_rep) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(chave) DO UPDATE SET "
            "tin=excluded.tin,tout=excluded.tout,cw=excluded.cw,cw1h=excluded.cw1h,cr=excluded.cr,ts=excluded.ts,dia=excluded.dia "
            "WHERE excluded.tout > uso.tout", linha)

    def inserir_lote(self, linhas: list[dict]) -> None:
        """Um lote numa só transação (um commit por linha seria lento demais ao ler o histórico inteiro)."""
        with self._trava, self._db:
            for l in linhas:
                self._gravar(self._tupla(**l))

    def ao_vivo(self, provedor: str, modelo: str = "", uso: dict | None = None, custo_rep: float | None = None,
                ts: float | None = None) -> None:
        self.inserir(ts=ts or time.time(), fonte="ao_vivo", provedor=provedor, modelo=modelo, uso=uso, custo_rep=custo_rep)

    def posicao(self, arquivo: str) -> tuple[int, float]:
        with self._trava:
            r = self._db.execute("SELECT posicao,mtime FROM coleta WHERE arquivo=?", (arquivo,)).fetchone()
        return (r["posicao"], r["mtime"]) if r else (0, 0.0)

    def marcar_posicao(self, arquivo: str, posicao: int, mtime: float) -> None:
        with self._trava, self._db:
            self._db.execute("INSERT INTO coleta(arquivo,posicao,mtime) VALUES(?,?,?) ON CONFLICT(arquivo) DO UPDATE SET posicao=?,mtime=?",
                             (arquivo, posicao, mtime, posicao, mtime))

    def meta(self, chave: str, padrao: str = "") -> str:
        with self._trava:
            r = self._db.execute("SELECT valor FROM meta WHERE chave=?", (chave,)).fetchone()
        return r["valor"] if r else padrao

    def definir_meta(self, chave: str, valor: str) -> None:
        with self._trava, self._db:
            self._db.execute("INSERT INTO meta(chave,valor) VALUES(?,?) ON CONFLICT(chave) DO UPDATE SET valor=?", (chave, valor, valor))

    def apagar_tudo(self) -> None:
        with self._trava, self._db:
            self._db.execute("DELETE FROM uso")
            self._db.execute("DELETE FROM coleta")

    # ── leitura ──────────────────────────────────────────────────────────
    def linhas(self, desde: float = 0.0, ate: float | None = None, tabela: dict | None = None, **filtros) -> list[dict]:
        """Linhas do período já com `custo` (USD) e `preco_ok`. Filtros: provedor, modelo, projeto, sessao, sub."""
        tabela = tabela or precos.carregar()
        sql, args = "SELECT * FROM uso WHERE ts>=? AND ts<?", [desde, ate if ate is not None else 4e12]
        for campo in ("provedor", "modelo", "projeto", "sessao"):
            if filtros.get(campo):
                sql += f" AND {campo}=?"
                args.append(filtros[campo])
        if filtros.get("sub") is not None and filtros.get("sub") != "":
            sql += " AND sub=?"
            args.append(int(bool(filtros["sub"])))
        with self._trava:
            brutas = self._db.execute(sql + " ORDER BY ts", args).fetchall()
        return [self._completar(dict(r), tabela) for r in brutas]

    @staticmethod
    def _completar(linha: dict, tabela: dict) -> dict:
        uso = {"in": linha["tin"], "out": linha["tout"], "cw": linha["cw"], "cw1h": linha["cw1h"], "cr": linha["cr"]}
        if linha["provedor"] in GRATIS:
            linha["custo"], linha["preco_ok"], linha["estimado"] = 0.0, True, False
        elif linha["custo_rep"] is not None:
            linha["custo"], linha["preco_ok"], linha["estimado"] = float(linha["custo_rep"]), True, False
        else:
            linha["custo"], linha["preco_ok"] = precos.calcular(linha["modelo"], uso, tabela)
            linha["estimado"] = True
        return linha
