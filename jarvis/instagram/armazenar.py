"""Armazenamento local em SQLite (instagram.db, fora do Git): análise, perfis, rodadas e posts públicos.

Guarda só métricas públicas e o começo da legenda (200 caracteres). Nada de comentários, seguidores nominais ou mídia.
O post é identificado por (rodada, chave): reimportar a mesma rodada atualiza em vez de duplicar.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

from jarvis import config
from jarvis.instagram import CAMPOS_NUMERICOS
from jarvis.instagram.importar import chave_post

SCHEMA = """
CREATE TABLE IF NOT EXISTS analise (id INTEGER PRIMARY KEY CHECK (id = 1), dados TEXT NOT NULL, atualizado TEXT);
CREATE TABLE IF NOT EXISTS perfil (arroba TEXT PRIMARY KEY, seguidores INTEGER, proprio INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS rodada (id INTEGER PRIMARY KEY AUTOINCREMENT, criada TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS post (rodada_id INTEGER NOT NULL, chave TEXT NOT NULL, perfil TEXT NOT NULL, link TEXT, data TEXT, formato TEXT,
  legenda TEXT, likes INTEGER, comentarios INTEGER, views INTEGER, salvamentos INTEGER, compartilhamentos INTEGER,
  PRIMARY KEY (rodada_id, chave));
"""
VERSAO_ESQUEMA = 2  # 1 = esquema original (sem versão gravada); 2 = no máximo um perfil "próprio" (índice único parcial)


def caminho() -> Path:
    return config.data_dir() / "instagram.db"


class Armazem:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path or caminho())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=15)) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            self._migrar(db)

    @staticmethod
    def _migrar(db: sqlite3.Connection) -> None:
        """Versão do esquema em PRAGMA user_version. Banco de versão mais nova (downgrade) é tolerado e não é rebaixado."""
        versao = db.execute("PRAGMA user_version").fetchone()[0]
        if versao >= VERSAO_ESQUEMA:
            return
        db.execute("BEGIN IMMEDIATE")
        try:
            if versao < 2:  # bancos antigos podem ter 2+ "próprios": fica o de maior id de linha, os outros viram concorrentes
                db.execute("UPDATE perfil SET proprio = 0 WHERE proprio = 1 AND rowid <> (SELECT MAX(rowid) FROM perfil WHERE proprio = 1)")
                db.execute("CREATE UNIQUE INDEX IF NOT EXISTS perfil_um_proprio ON perfil(proprio) WHERE proprio = 1")
            db.execute(f"PRAGMA user_version = {VERSAO_ESQUEMA}")
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    # ── análise (respostas da entrevista) e perfis ───────────────────────
    def analise(self) -> dict:
        with closing(self._db()) as db:
            linha = db.execute("SELECT dados FROM analise WHERE id = 1").fetchone()
        return json.loads(linha["dados"]) if linha else {}

    def salvar_analise(self, dados: dict) -> None:
        with closing(self._db()) as db, db:
            db.execute("INSERT OR REPLACE INTO analise (id, dados, atualizado) VALUES (1, ?, ?)",
                       (json.dumps(dados, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")))

    def definir_perfis(self, seguidores: dict[str, int | None], proprio: str = "") -> None:
        with closing(self._db()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            if proprio:  # no máximo um próprio: zera os outros antes (o índice único parcial exigiria, e o REPLACE apagaria a linha)
                db.execute("UPDATE perfil SET proprio = 0 WHERE proprio = 1 AND arroba <> ?", (proprio,))
            for arroba, seg in seguidores.items():
                atual = db.execute("SELECT seguidores FROM perfil WHERE arroba = ?", (arroba,)).fetchone()
                db.execute("INSERT OR REPLACE INTO perfil (arroba, seguidores, proprio) VALUES (?, ?, ?)",
                           (arroba, seg if seg is not None else (atual["seguidores"] if atual else None), int(arroba == proprio)))

    def seguidores(self) -> dict[str, int | None]:
        with closing(self._db()) as db:
            return {r["arroba"]: r["seguidores"] for r in db.execute("SELECT arroba, seguidores FROM perfil")}

    # ── rodadas e posts ──────────────────────────────────────────────────
    def rodadas(self) -> list[dict]:
        with closing(self._db()) as db:
            return [dict(r) for r in db.execute("SELECT r.id, r.criada, (SELECT COUNT(*) FROM post p WHERE p.rodada_id = r.id) AS posts "
                                                "FROM rodada r ORDER BY r.id")]

    def rodada_para_importar(self, agora: datetime, nova: bool = False) -> int:
        """A última rodada, se for da mesma semana ISO; senão (ou se pedido) uma rodada nova."""
        with closing(self._db()) as db, db:
            db.execute("BEGIN IMMEDIATE")  # ler a última e criar a nova numa só transação: duas chamadas não criam rodada duplicada
            ultima = db.execute("SELECT id, criada FROM rodada ORDER BY id DESC LIMIT 1").fetchone()
            if ultima and not nova and datetime.fromisoformat(ultima["criada"]).isocalendar()[:2] == agora.isocalendar()[:2]:
                return ultima["id"]
            return db.execute("INSERT INTO rodada (criada) VALUES (?)", (agora.isoformat(timespec="seconds"),)).lastrowid

    def gravar_posts(self, rodada_id: int, posts: list[dict]) -> tuple[int, int]:
        """Devolve (novos, atualizados)."""
        novos = atualizados = 0
        with closing(self._db()) as db, db:
            for p in posts:
                chave = chave_post(p)
                existe = db.execute("SELECT 1 FROM post WHERE rodada_id = ? AND chave = ?", (rodada_id, chave)).fetchone()
                db.execute("INSERT OR REPLACE INTO post (rodada_id, chave, perfil, link, data, formato, legenda, "
                           + ", ".join(CAMPOS_NUMERICOS) + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                           (rodada_id, chave, p["perfil"], p.get("link", ""), p.get("data", ""), p.get("formato", ""), p.get("legenda", ""),
                            *(p.get(c) for c in CAMPOS_NUMERICOS)))
                atualizados, novos = (atualizados + 1, novos) if existe else (atualizados, novos + 1)
        return novos, atualizados

    def posts(self, rodada_id: int) -> list[dict]:
        with closing(self._db()) as db:
            linhas = db.execute("SELECT * FROM post WHERE rodada_id = ? ORDER BY perfil, data, chave", (rodada_id,)).fetchall()
        return [{k: r[k] for k in r.keys() if k not in ("rodada_id", "chave")} for r in linhas]

    # ── apagar ───────────────────────────────────────────────────────────
    def apagar_perfil(self, arroba: str) -> int:
        with closing(self._db()) as db, db:
            n = db.execute("DELETE FROM post WHERE perfil = ?", (arroba,)).rowcount
            db.execute("DELETE FROM perfil WHERE arroba = ?", (arroba,))
        return n

    def apagar_tudo(self) -> None:
        with closing(self._db()) as db, db:
            for tabela in ("post", "rodada", "perfil", "analise"):
                db.execute(f"DELETE FROM {tabela}")


def ultima_rodada_em(path: Path | None = None) -> datetime | None:
    """Quando foi a última rodada (None se nunca houve). Não cria o banco se ele não existe."""
    path = Path(path or caminho())
    if not path.exists():
        return None
    todas = Armazem(path).rodadas()
    return datetime.fromisoformat(todas[-1]["criada"]) if todas else None
