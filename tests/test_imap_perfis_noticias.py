"""IMAP somente leitura, perfis de modelo, notícias por assunto, comandos locais e briefing."""

import imaplib
from datetime import datetime

import pytest

from jarvis import briefing
from jarvis.brains import perfis
from jarvis.config import Config
from jarvis.info import news
from jarvis.local.engine import LocalEngine
from jarvis.mail import accounts, imap
from jarvis.mail.base import MailError, split_id

RAW_HEADER = (b"From: =?UTF-8?Q?Jo=C3=A3o?= <j@x.com>\r\nSubject: =?UTF-8?B?RmF0dXJhIHZlbmNl?=\r\n"
              b"Date: Tue, 20 Oct 2026 08:00:00 -0300\r\nList-Unsubscribe: <mailto:u@x.com>\r\n\r\n")


class FakeImap:
    instancia = None

    def __init__(self, host, porta, timeout=0):
        FakeImap.instancia, self.chamadas, self.host = self, [], host

    def login(self, u, s):
        self.chamadas.append(("login", u))

    def select(self, caixa, readonly=False):
        self.chamadas.append(("select", caixa, readonly))
        return "OK", [b"1"]

    def uid(self, cmd, *args):
        self.chamadas.append((cmd,) + args)
        if cmd == "SEARCH":
            return "OK", [b"10 11 12"]
        return "OK", [(b"1 (FLAGS (\\Seen) BODY[HEADER] {10}", RAW_HEADER), (b" BODY[TEXT]<0> {5}", b"Ola, pague hoje."), b")"]

    def logout(self):
        self.chamadas.append(("logout",))


def conta():
    return imap.ImapAccount({"apelido": "Yahoo", "host": "imap.mail.yahoo.com", "porta": 993, "usuario": "u@y.com"},
                            senha="app-pass", fabrica=FakeImap)


def test_imap_so_le_com_ssl_readonly_e_peek():
    [a, *_] = conta().list_recent(2, False)
    box = FakeImap.instancia
    assert ("select", "INBOX", True) in box.chamadas
    fetch = next(c for c in box.chamadas if c[0] == "FETCH")
    assert "BODY.PEEK[HEADER]" in fetch[2] and "BODY.PEEK[TEXT]" in fetch[2]
    proibidos = {"STORE", "COPY", "EXPUNGE", "DELETE", "APPEND"}
    assert not any(c[0] in proibidos for c in box.chamadas) and box.chamadas[-1] == ("logout",)
    assert a.assunto == "Fatura vence" and a.remetente.startswith("João") and a.lista and not a.nao_lido
    assert a.id == "imap-yahoo:12" and "pague" in a.previa


def test_imap_nao_marca_e_host_precisa_estar_na_lista():
    with pytest.raises(MailError):
        conta().apply_category(["1"], "Importante")
    with pytest.raises(ValueError):
        imap.validar_host("evil.example.com")
    ruim = imap.ImapAccount({"apelido": "x", "host": "evil.example.com", "usuario": "u"}, senha="s", fabrica=FakeImap)
    with pytest.raises(ValueError):
        ruim.list_recent(1, False)


def test_imap_senha_vai_para_o_cofre_e_erro_nao_vaza(monkeypatch):
    cofre = {}
    monkeypatch.setattr("jarvis.keys.set_key", lambda p, k: cofre.__setitem__(p, k))
    cfg = Config()
    imap.conectar(cfg, "Yahoo", "imap.mail.yahoo.com", "u@y.com", "segredo-app")
    assert cofre == {"imap:Yahoo": "segredo-app"} and "segredo-app" not in str(cfg.email.imap)
    assert "imap-yahoo" in accounts(cfg) and split_id("imap-yahoo:5") == ("imap-yahoo", "5")

    def falha(*a, **k):
        raise imaplib.IMAP4.error("LOGIN failed segredo-app")

    ruim = imap.ImapAccount(cfg.email.imap[0], senha="segredo-app", fabrica=falha)
    with pytest.raises(MailError) as e:
        ruim.list_recent(1, False)
    assert "segredo-app" not in str(e.value)


def test_perfis_sem_id_fixo_por_padrao():
    cfg = Config()
    assert perfis.modelo_do_perfil(cfg) == "" and perfis.claude_config(cfg).model == ""
    cfg.claude.model = "meu-modelo"
    assert perfis.claude_config(cfg).model == "meu-modelo"
    perfis.definir(cfg, "economico", perfis.SUGESTOES["economico"])
    assert perfis.claude_config(cfg).model == "claude-haiku-5-5" and cfg.claude.model == "meu-modelo"
    perfis.definir(cfg, "maximo")  # sem modelo: perfil vazio = o de claude.model
    assert perfis.claude_config(cfg).model == "meu-modelo"
    with pytest.raises(ValueError):
        perfis.definir(cfg, "turbo")


GN = (b'<rss><channel><item><title>IA muda o mercado - Folha</title><link>https://n/1</link><pubDate>Tue, 20 Oct 2026 10:00:00 GMT</pubDate></item>'
      b'<item><title>IA muda o mercado - UOL</title><link>https://n/2</link><pubDate>Tue, 20 Oct 2026 09:00:00 GMT</pubDate></item>'
      b'<item><title>Outra noticia sem fonte</title><link>https://n/3</link><pubDate>Tue, 20 Oct 2026 08:00:00 GMT</pubDate></item></channel></rss>')


class RespNoticia:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, n=None):
        return GN


def test_noticias_por_assunto_separa_fonte_dedupe_e_cache():
    news._cache_mem.clear()
    urls = []

    def opener(req, timeout=0):
        urls.append(req.full_url)
        return RespNoticia()

    r = news.por_assunto("inteligência artificial", 5, opener, agora=1000)
    assert [(h["titulo"], h["fonte"]) for h in r["manchetes"]] == [("IA muda o mercado", "Folha"), ("Outra noticia sem fonte", "Google News")]
    assert "q=intelig%C3%AAncia%20artificial" in urls[0] and "hl=pt-BR" in urls[0]
    news.por_assunto("inteligência artificial", 5, opener, agora=1000 + 44 * 60)
    assert len(urls) == 1
    news.por_assunto("inteligência artificial", 5, opener, agora=1000 + 46 * 60)
    assert len(urls) == 2


def test_noticias_assunto_com_falha_vira_aviso():
    news._cache_mem.clear()

    def quebra(req, timeout=0):
        raise OSError("sem rede")

    r = news.por_assunto("dólar", 3, quebra)
    assert r["manchetes"] == [] and "não consegui" in r["avisos"][0]


@pytest.mark.parametrize("frase,intencao", [
    ("minha agenda", "agenda_hoje"), ("o que eu tenho hoje?", "agenda_hoje"), ("Jarvis, agenda de hoje", "agenda_hoje"),
    ("próximo compromisso", "agenda_proximo"), ("qual é o meu próximo compromisso", "agenda_proximo"),
    ("agenda da semana", "agenda_semana"), ("minha agenda da semana", "agenda_semana"),
    ("notícias de inteligência artificial", "noticias_assunto"), ("notícias sobre dólar", "noticias_assunto"),
    ("meus e-mails", "emails"), ("meus emails", "emails"), ("tem e-mail importante?", "email_importante"),
    ("bom dia", "bom_dia"), ("Jarvis, bom dia", "bom_dia"),
    ("notícias de tecnologia", "noticias"), ("notícias de hoje", "noticias"), ("notícias", "noticias"),
])
def test_comandos_locais(frase, intencao):
    motor = LocalEngine(load_config=Config)
    assert motor.classify(frase)[0] == intencao
    assert motor.is_direct_command(frase)  # direto: resolve na hora, sem gastar IA


def test_comando_noticias_de_x_chama_o_assunto(monkeypatch):
    visto = {}
    monkeypatch.setattr(news, "por_assunto", lambda a, n=5, **k: visto.setdefault("a", a) and {"manchetes": [{"titulo": "T", "fonte": "F", "link": "L"}], "avisos": []})
    out = LocalEngine(load_config=Config).handle("notícias de inteligência artificial")
    assert visto["a"] == "inteligencia artificial" and "T (F) L" in out


def test_comando_agenda_sem_agenda_conectada(monkeypatch, tmp_path):
    monkeypatch.setattr("jarvis.agenda.fontes.links", lambda cfg: [])
    assert "Nenhuma agenda conectada" in LocalEngine(load_config=Config).handle("minha agenda")


def clima(_):
    raise briefing.weather.WeatherError("x")


def test_briefing_inclui_agenda_e_emails_so_na_primeira_vez(tmp_path):
    cfg, estado = Config(), tmp_path / "e.json"
    cfg.city = ""
    chamadas = []

    def agenda(c):
        chamadas.append("a")
        return "**Agenda de hoje (1):**\n- 09:00: Dentista", "Você tem 1 compromisso hoje: Dentista às 09:00."

    kw = dict(now=datetime(2026, 10, 20, 8), state_path=estado, get_news=lambda k, n: {"manchetes": []},
              get_jobs=lambda c: ("", ""), get_agenda=agenda, get_emails=lambda c: ("**E-mails:** 2 de ação", "Você tem 2 e-mails pedindo ação."))
    primeira = briefing.build(cfg, **kw)
    assert "Dentista" in primeira["text"] and "2 e-mails pedindo ação" in primeira["speak"] and primeira["completo"]
    segunda = briefing.build(cfg, **kw)  # no mesmo dia: não repete
    assert not segunda["completo"] and "Dentista" not in segunda["text"] and chamadas == ["a"]
    forcada = briefing.build(cfg, forcar=True, **kw)  # "bom dia" pedido: completo de novo
    assert forcada["completo"] and "Dentista" in forcada["text"]


def test_briefing_agenda_e_emails_vazios_sem_conexao():
    cfg = Config()
    assert briefing.agenda_hoje(cfg) == ("", "") and briefing.emails_acao(cfg) == ("", "")
