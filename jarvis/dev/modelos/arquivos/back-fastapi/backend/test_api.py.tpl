import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    return TestClient(main.app)


def test_saude(client):
    assert client.get("/api/saude").json() == {"status": "ok"}


def test_crud_completo(client):
    criado = client.post("/api/itens", json={"titulo": "  Primeira tarefa  "})
    assert criado.status_code == 201
    assert criado.json() == {"id": 1, "titulo": "Primeira tarefa", "concluido": False}

    assert client.patch("/api/itens/1", json={"concluido": True}).json()["concluido"] is True
    assert [i["titulo"] for i in client.get("/api/itens").json()] == ["Primeira tarefa"]

    assert client.delete("/api/itens/1").status_code == 204
    assert client.get("/api/itens").json() == []


def test_validacao_e_nao_encontrado(client):
    assert client.post("/api/itens", json={"titulo": ""}).status_code == 422
    assert client.patch("/api/itens/99", json={"concluido": True}).status_code == 404
    assert client.delete("/api/itens/99").status_code == 404
