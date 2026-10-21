"""Regressão da auditoria de segurança das versões 0.21-0.23: cada teste falha sem a correção correspondente."""

import imaplib
import json
import socket
import ssl
import time
import urllib.request
from datetime import datetime

import pytest

from jarvis.agenda import ics, ocorrencias, servico, tz
from jarvis.instagram import importar
from jarvis.mail import imap
from jarvis.mobile import servidor as srv
from jarvis.mobile.pareamento import Pareamento
from jarvis.uso import exportar
from jarvis.uso.registro import Registro


# ── IMAP: o TLS precisa verificar certificado e nome do servidor ─────────────────────────────
def test_imap_padrao_verifica_certificado_e_nome(monkeypatch):
    visto = {}

    class Falso:
        def __init__(self, host, porta, **kw):
            visto.update(kw)

    monkeypatch.setattr(imaplib, "IMAP4_SSL", Falso)
    imap._conexao_segura("imap.gmail.com", 993, timeout=5)
    contexto = visto["ssl_context"]
    assert contexto.verify_mode == ssl.CERT_REQUIRED and contexto.check_hostname is True
    assert imap.ImapAccount({"apelido": "x", "host": "imap.gmail.com"})._fabrica is imap._conexao_segura


# ── Agenda: o link vem de fora; nada de rede interna, nem por DNS, nem por redirecionamento ────
def _dns(monkeypatch, ip):
    monkeypatch.setattr(socket, "getaddrinfo", lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))])


def test_baixar_recusa_nome_que_resolve_para_rede_interna(monkeypatch):
    _dns(monkeypatch, "127.0.0.1")
    with pytest.raises(ValueError):
        servico.baixar("https://agenda.exemplo.com/a.ics")
    _dns(monkeypatch, "192.168.0.10")
    with pytest.raises(ValueError):
        servico.baixar("https://agenda.exemplo.com/a.ics")
    _dns(monkeypatch, "169.254.169.254")
    with pytest.raises(ValueError):
        servico.checar_destino("https://metadata.exemplo.com/")


def test_baixar_aceita_destino_publico_com_opener_injetado(monkeypatch):
    _dns(monkeypatch, "8.8.8.8")
    servico.checar_destino("https://agenda.exemplo.com/a.ics")  # não levanta


def test_redirecionamento_para_rede_interna_ou_http_e_recusado(monkeypatch):
    _dns(monkeypatch, "8.8.8.8")
    gerente = servico._SoDestinoPublico()
    pedido = urllib.request.Request("https://agenda.exemplo.com/a.ics")
    for destino in ("http://agenda.exemplo.com/x", "https://127.0.0.1/x", "https://localhost/x", "https://10.0.0.5/x"):
        with pytest.raises(ValueError):
            gerente.redirect_request(pedido, None, 302, "Found", {}, destino)
    _dns(monkeypatch, "127.0.0.1")
    with pytest.raises(ValueError):
        gerente.redirect_request(pedido, None, 302, "Found", {}, "https://rebind.exemplo.com/x")


# ── Agenda: um evento com recorrência absurda não pode derrubar a agenda inteira ───────────────
def test_evento_com_recorrencia_fora_do_calendario_so_ignora_esse_evento():
    texto = ("BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:ruim\nSUMMARY:ruim\nDTSTART:20260101T100000Z\nRRULE:FREQ=YEARLY;INTERVAL=100000;COUNT=5\nEND:VEVENT\n"
             "BEGIN:VEVENT\nUID:bom\nSUMMARY:bom\nDTSTART:20261021T100000Z\nEND:VEVENT\nEND:VCALENDAR")
    z = tz.local()
    achadas = ocorrencias.ocorrencias(ics.ler(texto), datetime(2026, 10, 20, tzinfo=z), datetime(2026, 10, 27, tzinfo=z), z)
    assert [o.titulo for o in achadas] == ["bom"]


# ── Uso: exportar CSV sem fórmula em NENHUMA coluna de texto; importar sem estourar ───────────
def _reg(tmp_path):
    return Registro(tmp_path / "uso.db")


def test_csv_neutraliza_formula_no_provedor_e_no_dia(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    origem = {"versao": 1, "linhas": [{"ts": time.time(), "provedor": "=HYPERLINK(\"http://x\",\"a\")", "modelo": "\t=1+1", "tin": 1}]}
    reg = _reg(tmp_path)
    exportar.importar_json(reg, json.dumps(origem))
    linhas = exportar.exportar_csv(reg).splitlines()[1:]
    assert linhas
    for celula in next(__import__("csv").reader([linhas[0]])):
        assert celula[:1] not in ("=", "+", "@", "\t", "\r")


@pytest.mark.parametrize("ts", [1e300, float("inf"), -5, 0])
def test_importar_uso_ignora_data_impossivel_e_numero_gigante(tmp_path, monkeypatch, ts):
    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    reg = _reg(tmp_path)
    arquivo = '{"versao":1,"linhas":[{"ts":%s,"provedor":"claude","tin":1},{"ts":1760000000,"provedor":"claude","tin":1e30,"tout":99999999999999999999999}]}' % (
        "Infinity" if ts == float("inf") else repr(ts))
    assert exportar.importar_json(reg, arquivo)["linhas"] == 1  # a linha boa entra; a impossível não derruba o resto
    assert reg.linhas()[0]["tin"] <= 10**12


# ── Instagram: número impossível vira n/d em vez de quebrar a importação ──────────────────────
@pytest.mark.parametrize("texto", ['[{"perfil":"@a","link":"https://instagram.com/p/AB/","likes":Infinity}]',
                                   'perfil,link,likes\n@a,https://instagram.com/p/AB/,' + "9" * 5000,
                                   '[{"perfil":"@a","link":"https://instagram.com/p/AB/","likes":1e30}]'],
                         ids=["infinito", "digitos_demais", "notacao_gigante"])
def test_instagram_numero_absurdo_vira_nd(texto):
    r = importar.ler(texto)
    assert r["posts"][0]["likes"] is None


def test_instagram_numero_normal_continua_valendo():
    assert importar.numero("1,2 mil") == 1200 and importar.numero("3.4K") == 3400 and importar.numero(1234) == 1234


# ── Servidor do celular: conexão parada é derrubada (sem prender uma thread para sempre) ──────
def test_servidor_derruba_conexao_que_nao_termina_o_pedido(tmp_path, monkeypatch):
    monkeypatch.setattr(srv, "TIMEOUT_CONEXAO", 1)
    s = srv.ServidorCelular(Pareamento(tmp_path / "c.json"), lambda t: {"text": "ok"})
    url = s.iniciar(porta=0, rede=False)
    try:
        porta = int(url.rsplit(":", 1)[1])
        with socket.create_connection(("127.0.0.1", porta), timeout=5) as c:
            c.sendall(b"GET / HTTP/1.1\r\nHost: x\r\n")  # cabeçalho nunca termina
            c.settimeout(5)
            inicio = time.monotonic()
            try:
                restante = c.recv(100)
            except (ConnectionError, TimeoutError):
                restante = b""
            assert restante == b"" or restante.startswith(b"HTTP/1.1 4")
            assert time.monotonic() - inicio < 4
    finally:
        s.parar()
