"""Ponte api_leitura: validação dos argumentos e respostas sem segredo."""

import pytest

from jarvis.ui import api_leitura
from jarvis.ui.api_leitura import LeituraMixin, validar_item


class FakeLeitor:
    def __init__(self):
        self.itens = []

    def iniciar(self, item):
        self.itens.append(item)
        return {"estado": "lendo", "mensagem": ""}

    def estado(self):
        return {"estado": "parado", "mensagem": ""}

    def parar(self):
        return {"estado": "parado", "mensagem": "Leitura parada."}

    def continuar(self):
        return {"estado": "lendo", "mensagem": ""}


class Ponte(LeituraMixin):
    def __init__(self):
        self._leitor = FakeLeitor()


@pytest.mark.parametrize("ruim", [
    None, "texto", [], {}, {"tipo": "outro", "titulo": "a b c"}, {"tipo": "noticia"},
    {"tipo": "noticia", "titulo": 5}, {"tipo": "noticia", "titulo": "ok título", "url": "file:///c:/x"},
    {"tipo": "noticia", "titulo": "ok título", "url": "http://127.0.0.1/x"},
    {"tipo": "noticia", "titulo": "ok título", "idioma": "xx"}, {"tipo": ["noticia"], "titulo": "ok título"},
])
def test_item_invalido_e_recusado(ruim):
    p = Ponte()
    r = p.ler_item(ruim)
    assert r["ok"] is False and r["estado"] == "parado" and p._leitor.itens == []


def test_item_valido_normaliza_e_limita():
    p = Ponte()
    r = p.ler_item({"tipo": "vaga", "titulo": "T" * 5000, "trecho": "a\x00b" * 10000, "url": "https://site.example/v", "completo": True, "extra": "x"})
    it = p._leitor.itens[0]
    assert r["ok"] and len(it["titulo"]) == api_leitura.MAX_TITULO and len(it["trecho"]) <= api_leitura.MAX_TRECHO
    assert "\x00" not in it["trecho"] and it["completo"] is True and "extra" not in it


def test_completo_sem_url_e_ignorado():
    assert validar_item({"tipo": "clima", "titulo": "Chuva forte hoje", "completo": True})["completo"] is False


def test_parar_estado_continuar():
    p = Ponte()
    assert p.parar_leitura()["ok"] and p.estado_leitura()["ok"] and p.continuar_leitura()["ok"]


def test_resposta_nao_traz_url_nem_chave():
    p = Ponte()
    r = p.ler_item({"tipo": "noticia", "titulo": "Manchete boa", "url": "https://s.example/a?token=SEGREDO"})
    assert "SEGREDO" not in str(r)


def test_api_expoe_os_metodos():
    from jarvis.ui.api import Api

    for nome in ("ler_item", "parar_leitura", "continuar_leitura", "estado_leitura"):
        assert callable(getattr(Api, nome))
