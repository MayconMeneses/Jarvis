"""Correções de qualidade do backend das versões 0.21-0.23: cache de agenda, triagem, frases ambíguas."""

from datetime import datetime, timedelta, timezone

from jarvis import keys
from jarvis.agenda import fontes, servico
from jarvis.config import Config
from jarvis.local.engine import LocalEngine
from jarvis.mail import triagem
from jarvis.mail.base import Mail

BRT = timezone(timedelta(hours=-3))
CAL = "BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:1\r\nDTSTART:20261020T130000Z\r\nSUMMARY:{}\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n"


class Resp:
    def __init__(self, texto):
        self.texto = texto.encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=None):
        return self.texto


def test_cache_da_agenda_depende_do_link_e_relogio_voltado_nao_congela(tmp_path):
    chamadas = []

    def rede(pedido, timeout=0):
        chamadas.append(pedido.full_url)
        return Resp(CAL.format("A" if "um" in pedido.full_url else "B"))

    t1, _ = servico.obter("Pessoal", "https://x.test/um.ics", tmp_path, rede, 1000.0)
    t2, _ = servico.obter("Pessoal", "https://x.test/dois.ics", tmp_path, rede, 1001.0)  # mesmo apelido, outro link
    assert "SUMMARY:A" in t1 and "SUMMARY:B" in t2 and len(chamadas) == 2
    servico.obter("Pessoal", "https://x.test/dois.ics", tmp_path, rede, 500.0)  # relógio voltou: o cache não vale
    assert len(chamadas) == 3
    assert not list(tmp_path.glob("*.tmp"))  # a gravação atômica não deixa lixo


def test_remover_agenda_apaga_tambem_a_copia_em_cache(tmp_path, monkeypatch):
    cofre = {}
    monkeypatch.setattr(keys, "get_key", cofre.get)
    monkeypatch.setattr(keys, "set_key", cofre.__setitem__)
    monkeypatch.setattr(keys, "delete_key", lambda k: cofre.pop(k, None))
    monkeypatch.setattr(fontes, "pasta_cache", lambda: tmp_path)
    cfg = Config()
    fontes.adicionar(cfg, "Pessoal", "https://x.test/um.ics")
    servico.obter("Pessoal", "https://x.test/um.ics", tmp_path, lambda p, timeout=0: Resp(CAL.format("A")), 1.0)
    assert list(tmp_path.glob("*.ics"))
    fontes.remover(cfg, "Pessoal")
    assert not list(tmp_path.glob("*.ics")) and not cofre and cfg.agendas == []


def mail(remetente, assunto="Oi"):
    return Mail(id="gmail:1", conta="gmail", remetente=remetente, assunto=assunto, data="", previa="", nao_lido=True, lista=False)


def test_regra_editada_vale_na_hora_para_email_ja_visto(tmp_path):
    arq = tmp_path / "t.json"
    m = mail("chefe@x.com", "Newsletter com desconto")
    assert triagem.classificar(Config(), [m], lambda c, ms: {}, arq, agora=1000)["gmail:1"]["nivel"] == triagem.RUIDO
    cfg = Config()
    cfg.email.regras = [{"campo": "remetente", "contem": "chefe", "categoria": "Importante"}]
    out = triagem.classificar(cfg, [mail("chefe@x.com", "Newsletter com desconto")], lambda c, ms: {}, arq, agora=2000)["gmail:1"]
    assert out["nivel"] == triagem.ACAO and out["fonte"] == "regra"


def test_frases_ambiguas_do_motor_local():
    motor = LocalEngine()
    for frase in ("quanto gastei no mercado esse mês?", "quanto gasto com comida", "quanto usei de gasolina"):
        assert motor.classify(frase) is None or motor.classify(frase)[0] != "uso_ia", frase
    for frase in ("quanto gastei", "quanto gastei com IA", "quanto gastei de claude hoje", "quanto gastei no mês", "quanto usei esta semana"):
        assert motor.classify(frase)[0] == "uso_ia", frase
    for frase in ("bom dia", "Bom dia, Jarvis!", "boa tarde jarvis"):
        assert motor.classify(frase)[0] == "bom_dia", frase
    for frase in ("bom dia, me explica o que é um decorator", "bom dia amigo"):
        assert motor.classify(frase) is None or motor.classify(frase)[0] != "bom_dia", frase


# ── IMAP: reconexão e socket fechado ─────────────────────────────────────
import imaplib  # noqa: E402

from jarvis.mail import imap  # noqa: E402
from jarvis.mail.base import MailError  # noqa: E402

CONF = {"apelido": "Yahoo", "host": "imap.mail.yahoo.com", "porta": 993, "usuario": "u@y.com"}


class CaixaFalsa:
    abertas: list = []

    def __init__(self, host, porta, timeout=0, falhar_login=False, cair_na_busca=False):
        self.falhar_login, self.cair, self.fechada = falhar_login, cair_na_busca, False
        CaixaFalsa.abertas.append(self)

    def login(self, u, s):
        if self.falhar_login:
            raise imaplib.IMAP4.error("AUTHENTICATIONFAILED")

    def select(self, *a, **k):
        return "OK", [b"0"]

    def uid(self, cmd, *a):
        if self.cair:
            raise imaplib.IMAP4.abort("socket error: EOF")
        return "OK", [b""] if cmd == "SEARCH" else ("OK", [])

    def logout(self):
        self.fechada = True


def test_imap_login_recusado_fecha_o_socket_e_nao_repete():
    CaixaFalsa.abertas = []
    conta = imap.ImapAccount(CONF, senha="x", fabrica=lambda h, p, timeout=0: CaixaFalsa(h, p, timeout, falhar_login=True))
    try:
        conta.list_recent(5, True)
        assert False, "deveria falhar"
    except MailError as exc:
        assert "x" not in str(exc).replace("IMAP Yahoo: não consegui entrar (Error)", "")  # senha nunca aparece
    assert len(CaixaFalsa.abertas) == 1 and CaixaFalsa.abertas[0].fechada  # sem nova tentativa: evita bloquear a conta


def test_imap_reconecta_uma_vez_quando_a_conexao_cai_no_meio():
    CaixaFalsa.abertas = []
    n = {"i": 0}

    def fabrica(h, p, timeout=0):
        n["i"] += 1
        return CaixaFalsa(h, p, timeout, cair_na_busca=n["i"] == 1)

    assert imap.ImapAccount(CONF, senha="x", fabrica=fabrica).list_recent(5, True) == []
    assert n["i"] == 2 and all(c.fechada for c in CaixaFalsa.abertas)


def test_imap_cai_duas_vezes_vira_aviso_e_fecha_tudo():
    CaixaFalsa.abertas = []
    conta = imap.ImapAccount(CONF, senha="x", fabrica=lambda h, p, timeout=0: CaixaFalsa(h, p, timeout, cair_na_busca=True))
    try:
        conta.list_recent(5, True)
        assert False, "deveria falhar"
    except MailError as exc:
        assert "conexão caiu" in str(exc)
    assert len(CaixaFalsa.abertas) == 2 and all(c.fechada for c in CaixaFalsa.abertas)
