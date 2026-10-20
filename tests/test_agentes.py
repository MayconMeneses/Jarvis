import json
from types import SimpleNamespace

import pytest

from jarvis.agentes import estado as est
from jarvis.agentes import painel, uso_adaptador
from jarvis.agentes.catalogo import ACOES_PERMITIDAS, CATALOGO
from jarvis.agentes.registro import Registro
from jarvis.autonomo.agendador import Autonomo
from jarvis.config import Config

NOW = 1_800_000_000.0


def d(**kw):
    base = dict(ligado=True, cadencia=60.0, ultimo=NOW - 10, ultimo_estado="ok")
    base.update(kw)
    return est.decidir(NOW, **base)


def test_fronteira_stale_2_5x():
    assert d(ultimo=NOW - 150).state == est.OK       # exatamente 2,5 x: ainda ok
    assert d(ultimo=NOW - 150.01).state == est.STALE
    assert est.STALE_FATOR == 2.5


def test_ausencia_de_dado_nao_e_ok():
    assert d(ultimo=None, ultimo_estado=None).state == est.STALE
    assert d(ultimo=None, ultimo_estado=None, ocioso_legitimo=True).state == est.IDLE
    assert d(cadencia=None, ultimo=None, ultimo_estado=None, vivo=None).state == est.STALE


def test_desligado_por_config_nao_e_erro():
    assert d(ligado=False, ultimo_estado="erro").state == est.OFF


def test_erro_e_fase():
    assert d(ultimo_estado="erro").state == est.ERROR
    assert d(ultimo=NOW - 30).phase == 0.5
    assert d(ultimo=NOW - 100).phase == 1.0
    r = d(ultimo=NOW + 500)  # relógio recuado
    assert r.age_s == 0 and r.state == est.OK


def test_continuos_usam_predicado_vivo():
    c = dict(cadencia=None, ultimo=None, ultimo_estado=None)
    assert d(vivo=True, **c).state == est.OK
    assert d(vivo=False, **c).state == est.ERROR
    assert d(vivo=False, ocioso_legitimo=True, **c).state == est.IDLE


def test_ocupado_tolera_tarefa_longa_ate_o_limite():
    assert d(ultimo=NOW - 600, ocupado=True).state == est.OK
    assert d(ultimo=NOW - est.TOLERANCIA_OCUPADO_S - 1, ocupado=True).state == est.STALE


def test_resumo():
    r = est.resumo([est.OK, est.IDLE, est.OFF, est.STALE, est.ERROR])
    assert r == {"total": 5, "ok": 2, "atencao": 2, "off": 1, "pior": est.ERROR}
    assert est.resumo([])["pior"] == est.OK
    assert est.resumo([est.OFF, est.OK])["pior"] == est.OK


class MemFake:
    def __init__(self):
        self.d = {}

    def meta(self, k):
        return self.d.get(k)

    def set_meta(self, k, v):
        self.d[k] = v


def test_registro_grava_e_le_da_memoria():
    t = [NOW]
    mem = MemFake()
    r = Registro(relogio=lambda: t[0])
    r.ligar_memoria(mem)
    r.marcar("proativo", "ok")
    assert mem.d["agente:proativo:estado"] == "ok" and "agente:proativo:ultimo" in mem.d
    t[0] += 5
    r.marcar("proativo", "ok")  # dentro do intervalo e sem mudança: não regrava
    assert Registro(relogio=lambda: t[0]).ler("proativo") is None
    novo = Registro(relogio=lambda: t[0])
    novo.ligar_memoria(mem)
    assert novo.ler("proativo").estado == "ok"
    r.marcar("proativo", "estado-inventado")  # nunca levanta
    assert r.ler("proativo").estado == "ok"


def cfg_com(**kw):
    c = Config()
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def test_retrato_estados_reais():
    r = Registro(relogio=lambda: NOW)
    r.marcar("proativo", "ok")
    r.marcar("sessoes", "erro", "X")
    cfg = cfg_com(proativo=True, autonomo=False, celular_ativo=True)
    out = painel.retrato(cfg, agora=NOW + 30, registro=r, vivos={"celular": True, "voz": False})
    por = {a["id"]: a for a in out["agentes"]}
    assert por["proativo"]["state"] == "ok" and por["proativo"]["phase"] == 0.5
    assert por["autonomo"]["state"] == "off"
    assert por["sessoes"]["state"] == "error"
    assert por["tarefas"]["state"] == "stale"  # nunca bateu: ausência de dado não é ok
    assert por["celular"]["state"] == "ok"
    assert por["atualizador"]["state"] == "off"  # fora da versão instalada
    assert out["resumo"]["pior"] == "error"
    assert out["resumo"]["total"] == len(CATALOGO)


def test_uso_adaptador_contrato():
    assert uso_adaptador.uso_atual(lambda: None) is None
    out = uso_adaptador.uso_atual(lambda: {"tokens_in": 5, "tokens_out": 2, "cache": 1, "custo_usd": 0.1, "segredo": "x"})
    assert set(out) == set(uso_adaptador.CHAVES) and out["estimado"] is True

    def quebra():
        raise RuntimeError

    assert uso_adaptador.uso_atual(quebra) is None


class MemAuto(MemFake):
    pass


def autonomo(avaliar, mem, quando):
    return Autonomo(lambda: cfg_com(autonomo=True), mem, lambda t: None, None, None, lambda t: [],
                    ultimo_pedido=lambda: 0.0, agora=lambda: quando, carga=lambda: (1.0, 1.0), avaliar_semana=avaliar)


def test_avaliacao_semanal_so_vira_feito_depois_do_sucesso():
    from datetime import datetime

    domingo = datetime(2026, 10, 18, 12, 0)
    mem, chamadas = MemAuto(), []
    mem.pedidos = []

    def falha():
        chamadas.append(1)
        raise RuntimeError("quebrou")

    a = autonomo(falha, mem, domingo)
    a._avaliacao_semanal(domingo)
    chave = f"autonomo:semana:{domingo:%G-%V}"
    assert mem.d[chave] == "erro:2026-10-18"
    a._avaliacao_semanal(domingo)  # mesmo dia: não repete
    assert len(chamadas) == 1
    ok = autonomo(lambda: "nota 8", mem, domingo.replace(day=25))  # outro dia, a marca de erro não vale
    mem.d.pop(chave)
    ok._avaliacao_semanal(domingo)
    assert mem.d[chave] == "feito"


def test_ids_da_lista_branca_nao_incluem_estudo_autonomo():
    assert "autonomo" not in ACOES_PERMITIDAS
    assert set(ACOES_PERMITIDAS.values()) == {"proativo_tick", "sessoes_tick", "check_update"}


PROIBIDAS = {"cwd", "pasta", "path", "caminho", "key", "chave", "secret", "segredo", "password", "senha", "bearer",
             "authorization", "result", "resultado", "prompt", "summary", "socket", "messagingSocketPath"}


def chaves(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from chaves(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from chaves(v)


@pytest.fixture
def api(monkeypatch, tmp_path):
    from jarvis.ui.api_agents import AgentsMixin

    class A(AgentsMixin):
        _voice = None
        _mobile = None

        def check_update(self):
            self.chamou = True

    monkeypatch.setattr("jarvis.config.load", lambda: cfg_com())
    a = A()
    a._subagentes = lambda: []
    return a


def test_agents_status_idempotente_sem_campos_proibidos(api):
    a = api
    a._provedor_uso = lambda: {"tokens_in": 1}
    r1, r2 = a.agents_status(), a.agents_status()
    for r in (r1, r2):
        r.pop("server_now")
    assert r1 == r2
    assert not PROIBIDAS & set(chaves(r1))
    assert not getattr(a, "chamou", False)  # leitura nunca executa ação
    json.dumps(r1)


def test_agents_run_lista_branca(api):
    assert api.agents_run("autonomo")["ok"] is False
    assert api.agents_run("../x")["ok"] is False
    assert api.agents_run("proativo")["ok"] is False  # ninguém registrou a ação
    chamadas = []
    api._registrar_acao("proativo_tick", lambda: chamadas.append(1))
    api._registrar_acao("estudar_agora", lambda: chamadas.append("proibido"))  # fora da lista: ignorada
    assert api.agents_run("proativo")["ok"] is True and chamadas == [1]
    assert api.agents_run("atualizador")["ok"] is True and api.chamou
    assert "estudar_agora" not in api._acoes_agentes
