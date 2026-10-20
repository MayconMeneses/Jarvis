"""Painel de agentes (constelação) e tela Agenda e e-mail: regras visuais puras, página estática e ponte sem segredos."""

import json
import re
import shutil
import subprocess

import pytest

from jarvis import config
from jarvis.ui import web
from jarvis.ui.api_agenda import AgendaMixin

ARQUIVOS_JS = ("agents-estado", "agents-desenho", "agents", "agenda-email")
SEGREDO_LINK = "https://calendar.google.com/calendar/ical/segredo123/private-token/basic.ics"
SEGREDO_SENHA = "senha-de-app-xyz-999"


def _node(expressao: str):
    """Roda uma expressão contra o módulo de regras puras no Node e devolve o JSON."""
    caminho = (web.BASE / "js" / "agents-estado.js").as_posix()
    codigo = f"const E = require({json.dumps(caminho)}); console.log(JSON.stringify({expressao}));"
    saida = subprocess.run(["node", "-e", codigo], capture_output=True, text=True, encoding="utf-8", timeout=30, check=True).stdout
    return json.loads(saida)


precisa_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node não instalado")


def _agente(**kw):
    base = {"id": "proativo", "state": "ok", "modo": "ciclico", "cadencia_s": 60, "age_s": 30}
    return {**base, **kw}


@precisa_node
@pytest.mark.parametrize("estado,cor", [("ok", "--ok"), ("stale", "--orange"), ("error", "--danger"), ("idle", "--cyan"), ("off", "--faint")])
def test_cor_do_estado_so_por_variavel_do_tema(estado, cor):
    v = _node(f"E.visual({json.dumps(_agente(state=estado))}, 30)")
    assert v["cor"] == f"var({cor})"


@precisa_node
def test_arco_do_ciclo_e_pulso_acima_de_92_por_cento():
    meio = _node(f"E.visual({json.dumps(_agente())}, 30)")
    assert meio["modo"] == "arco" and meio["arco"] == 0.5 and not meio["arcoPulsa"] and meio["pulsoLuz"]
    quase = _node(f"E.visual({json.dumps(_agente())}, 57)")
    assert quase["arcoPulsa"] is True
    assert _node(f"E.visual({json.dumps(_agente())}, 55.2)")["arcoPulsa"] is False  # 92% exatos: ainda não pulsa


@precisa_node
def test_continuo_gira_arco_curto_e_desligado_nao_desenha_arco():
    cont = _node(f"E.visual({json.dumps(_agente(modo='continuo', cadencia_s=5))}, 2)")
    assert cont["modo"] == "giro" and 0 < cont["arco"] < 0.5
    off = _node(f"E.visual({json.dumps(_agente(state='off'))}, 2)")
    assert off["modo"] == "nenhum" and off["apagado"] and not off["pulsoLuz"]


@precisa_node
def test_luz_so_de_saudavel_e_erro_pulsa():
    for estado in ("stale", "error", "idle", "off"):
        assert _node(f"E.visual({json.dumps(_agente(state=estado))}, 10)")["pulsoLuz"] is False
    erro = _node(f"E.visual({json.dumps(_agente(state='error'))}, 10)")
    assert erro["erroPulsa"] is True and erro["arco"] == 1


@precisa_node
def test_relogio_local_envelhece_e_vira_parado_depois_de_2_5_ciclos():
    a = json.dumps(_agente(age_s=100))
    assert _node(f"E.idadeLocal({a}, 5000)") == 105
    assert _node(f"E.estadoLocal({a}, 150)") == "ok"
    assert _node(f"E.estadoLocal({a}, 150.5)") == "stale"
    assert _node(f"E.idadeLocal({json.dumps(_agente(age_s=None))}, 5000)") is None
    assert _node(f"E.estadoLocal({json.dumps(_agente(state='bogus'))}, 1)") == "stale"  # estado desconhecido nunca vira "ok"


@precisa_node
def test_orbe_recebe_o_pior_estado():
    assert _node('E.paraOrbe({"pior":"error","atencao":1})') == "erro"
    assert _node('E.paraOrbe({"pior":"stale","atencao":1})') == "atencao"
    assert _node('E.paraOrbe({"pior":"ok","atencao":0})') == "ok"
    assert _node("E.paraOrbe(null)") == ""


@precisa_node
def test_geometria_e_satelite_custo_sempre_estimado():
    pos = _node("E.posicoes(4, 100, 100, 50, 40)")
    assert round(pos[0]["x"]) == 100 and round(pos[0]["y"]) == 60  # o primeiro fica no topo
    assert len(_node("E.hexagono(0, 0, 10)").split(" ")) == 6
    assert _node("E.arcoPath(0, 0, 10, 0, 0)") == ""
    s = _node('E.satelite({"estado":"concluido","fim":1000,"tokens":{"custo_usd":0.5,"tokens_total":1500}}, 1000)')
    assert "estimado" in s["custo"] and s["tokens"] == "1.5 k tokens"
    sem = _node('E.satelite({"estado":"rodando","tokens":{"custo_usd":null}}, 5)')
    assert "indisponível" in sem["custo"]
    velho = _node('E.satelite({"estado":"concluido","fim":0,"tokens":{}}, 99999)')
    assert velho["opacidade"] == 0.25


def test_pagina_tem_botoes_dialogos_e_scripts():
    pagina = web.page()
    for ident in ("bom-dia", "open-agentes", "open-agenda", 'id="agentes"', 'id="agenda-email"', "AgentesDesenho"):
        assert ident in pagina
    assert 'type="password"' in pagina and "Senhas de app" in pagina and "Integrar agenda" in pagina


def test_estatico_sem_innerhtml_cor_fixa_nem_fonte_externa():
    for nome in ARQUIVOS_JS:
        codigo = (web.BASE / "js" / f"{nome}.js").read_text(encoding="utf-8")
        assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function", codigo), nome
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|https?://(?!www\.w3\.org/2000/svg)", codigo), nome
    css = (web.BASE / "css" / "agents.css").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(|@import|url\(|fonts\.", css)


def test_rodar_agora_so_aparece_quando_o_backend_manda_acao():
    codigo = (web.BASE / "js" / "agents.js").read_text(encoding="utf-8")
    assert "if (a.acao)" in codigo and "agents_run" in codigo


@pytest.fixture
def cofre(monkeypatch):
    guardado = {}
    monkeypatch.setattr("jarvis.keys.set_key", lambda p, k: guardado.__setitem__(p, k))
    monkeypatch.setattr("jarvis.keys.get_key", lambda p: guardado.get(p))
    monkeypatch.setattr("jarvis.keys.delete_key", lambda p: guardado.pop(p, None))
    return guardado


def test_ponte_agenda_nao_devolve_o_link_e_guarda_no_cofre(cofre):
    api = AgendaMixin()
    r = api.conectar_agenda("Pessoal", SEGREDO_LINK, "verde")
    assert r["ok"] and cofre["ical:Pessoal"] == SEGREDO_LINK
    status = api.agenda_email_status()
    assert "segredo123" not in json.dumps(status) and status["agendas"] == [{"apelido": "Pessoal", "cor": "verde"}]
    assert "segredo123" not in json.dumps(config.load().agendas)
    ruim = api.conectar_agenda("X", "http://localhost/a.ics")
    assert ruim["ok"] is False and "localhost/a.ics" not in ruim["mensagem"]


def test_ponte_testar_agenda_erro_sem_vazar_o_link(cofre, monkeypatch):
    api = AgendaMixin()
    api.conectar_agenda("Pessoal", SEGREDO_LINK)

    def quebra(url, *a, **k):
        raise OSError(f"falha em {url}")

    monkeypatch.setattr("jarvis.agenda.servico.baixar", quebra)
    r = api.testar_agenda("Pessoal")
    assert r["ok"] is False and "segredo123" not in json.dumps(r)
    monkeypatch.setattr("jarvis.agenda.servico.baixar", lambda url, *a, **k: "BEGIN:VCALENDAR\nEND:VCALENDAR")
    assert api.testar_agenda("Pessoal")["ok"] is True
    assert api.testar_agenda("Inexistente")["ok"] is False


def test_ponte_imap_senha_nunca_volta_e_host_fora_da_lista_e_recusado(cofre, monkeypatch):
    api = AgendaMixin()
    r = api.conectar_imap("Gmail", "imap.gmail.com", "eu@gmail.com", f" {SEGREDO_SENHA} ")
    assert r["ok"] and cofre["imap:Gmail"] == SEGREDO_SENHA
    assert SEGREDO_SENHA not in json.dumps(r) and SEGREDO_SENHA not in json.dumps(api.agenda_email_status())
    ruim = api.conectar_imap("Mau", "imap.malvado.example", "a@b.c", SEGREDO_SENHA)
    assert ruim["ok"] is False and SEGREDO_SENHA not in json.dumps(ruim)

    from jarvis.mail.base import MailError

    def falha(self, *a, **k):
        raise MailError("IMAP Gmail: não consegui entrar (error)")

    monkeypatch.setattr("jarvis.mail.imap.ImapAccount.list_recent", falha)
    teste = api.testar_imap("Gmail")
    assert teste["ok"] is False and SEGREDO_SENHA not in json.dumps(teste)
    assert api.desconectar_imap("Gmail")["ok"] and "imap:Gmail" not in cofre


def test_resumo_de_uso_para_o_painel_tem_o_contrato(tmp_path):
    from jarvis.agentes import uso_adaptador
    from jarvis.uso import agentes
    from jarvis.uso.registro import Registro

    resumo = agentes.resumo_para_agentes(Registro(tmp_path / "uso.db"), 1_800_000_000.0)
    assert set(resumo) == {"tokens_in", "tokens_out", "cache", "custo_usd", "estimado", "origem"}
    assert uso_adaptador.uso_atual(lambda: resumo)["origem"] == "nenhum"
