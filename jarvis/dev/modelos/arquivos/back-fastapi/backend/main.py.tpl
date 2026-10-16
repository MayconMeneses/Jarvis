"""__NOME__: API de exemplo (FastAPI + SQLite). Troque "itens" pelas suas entidades.

Rodar:   uvicorn main:app --reload      (documentação interativa em http://localhost:8000/docs)
Testar:  pytest
"""

import os
import sqlite3
from contextlib import closing
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title="__NOME__")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8080", "http://127.0.0.1:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def conectar() -> sqlite3.Connection:
    """Uma conexão por requisição (SQLite é leve). O caminho pode ser trocado por DB_PATH."""
    db = sqlite3.connect(os.environ.get("DB_PATH", Path(__file__).with_name("dados.db")))
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS itens (id INTEGER PRIMARY KEY, titulo TEXT NOT NULL, concluido INTEGER NOT NULL DEFAULT 0)")
    return db


class NovoItem(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)


class Alteracao(BaseModel):
    concluido: bool


def como_dict(linha: sqlite3.Row) -> dict:
    return {"id": linha["id"], "titulo": linha["titulo"], "concluido": bool(linha["concluido"])}


@app.get("/api/saude")
def saude() -> dict:
    return {"status": "ok"}


@app.get("/api/itens")
def listar() -> list[dict]:
    with closing(conectar()) as db:
        return [como_dict(r) for r in db.execute("SELECT * FROM itens ORDER BY id")]


@app.post("/api/itens", status_code=201)
def criar(item: NovoItem) -> dict:
    with closing(conectar()) as db:
        cursor = db.execute("INSERT INTO itens (titulo) VALUES (?)", (item.titulo.strip(),))
        db.commit()
        return como_dict(db.execute("SELECT * FROM itens WHERE id = ?", (cursor.lastrowid,)).fetchone())


@app.patch("/api/itens/{item_id}")
def alterar(item_id: int, mudanca: Alteracao) -> dict:
    with closing(conectar()) as db:
        db.execute("UPDATE itens SET concluido = ? WHERE id = ?", (int(mudanca.concluido), item_id))
        db.commit()
        linha = db.execute("SELECT * FROM itens WHERE id = ?", (item_id,)).fetchone()
    if linha is None:
        raise HTTPException(status_code=404, detail="item não encontrado")
    return como_dict(linha)


@app.delete("/api/itens/{item_id}", status_code=204)
def apagar(item_id: int) -> None:
    with closing(conectar()) as db:
        apagados = db.execute("DELETE FROM itens WHERE id = ?", (item_id,)).rowcount
        db.commit()
    if not apagados:
        raise HTTPException(status_code=404, detail="item não encontrado")
