"""Pendências do backend: importação idempotente, preço único, Instagram versionado/atômico, fusos reais, aviso de rede."""

import sqlite3
import threading
import zoneinfo
from datetime import datetime, timedelta

import pytest

from jarvis.agenda import ics, ocorrencias, tz
from jarvis.config import Config
from jarvis.dev import subagentes
from jarvis.instagram import armazenar
from jarvis.instagram.armazenar import Armazem
from jarvis.uso import exportar, precos
from jarvis.uso.registro import Registro

AGORA = 1_900_000_000.0
USO = {"in": 10, "out": 20, "cw": 0, "cw1h": 0, "cr": 5}


# ── 1. importação idempotente ────────────────────────────────────────────
def test_reimportar_o_proprio_export_nao_duplica(tmp_path):
    reg = Registro(tmp_path / "a.db")
    reg.inserir(ts=AGORA, fonte="ao_vivo", provedor="claude", modelo="m", sessao="s", uso=USO)  # sem chave
    reg.inserir(ts=AGORA + 1, fonte="jsonl", provedor="claude", modelo="m", sessao="s", uso=USO, chave="msg1|req1")
    texto = exportar.exportar_json(reg)
    assert exportar.importar_json(reg, texto)["novas"] == 0  # no mesmo banco: nada novo
    assert len(reg.linhas()) == 2
    outro = Registro(tmp_path / "b.db")
    assert exportar.importar_json(outro, texto)["novas"] == 2
    assert exportar.importar_json(outro, texto)["novas"] == 0  # e de novo
    assert len(outro.linhas()) == 2


def test_importar_linha_diferente_ainda_entra(tmp_path):
    reg = Registro(tmp_path / "a.db")
    reg.inserir(ts=AGORA, fonte="ao_vivo", provedor="claude", modelo="m", sessao="s", uso=USO)
    texto = exportar.exportar_json(reg)
    reg.inserir(ts=AGORA, fonte="ao_vivo", provedor="claude", modelo="m", sessao="s", uso={**USO, "out": 21})
    assert exportar.importar_json(reg, texto)["novas"] == 0 and len(reg.linhas()) == 2


# ── 2. preço único ───────────────────────────────────────────────────────
def test_subagentes_usa_a_tabela_unica_de_precos(tmp_path, monkeypatch):
    assert not hasattr(subagentes, "PRECOS_USD_MTOK")
    t = {"in": 1_000_000, "out": 1_000_000, "cc": 0, "cr": 0}
    assert subagentes.custo_estimado("claude-opus-4-1-20250805", t) == 90.0  # família opus da tabela única
    assert subagentes.custo_estimado("modelo-desconhecido", t) is None
    editada = tmp_path / "p.json"
    precos.salvar({"modelos": {"claude-opus-5-5": {"in": 1, "out": 2}}}, editada)
    monkeypatch.setattr(precos, "arquivo", lambda: editada)
    assert subagentes.custo_estimado("claude-opus-4-1", t) == 3.0  # preço editado pelo dono vale também aqui


def test_calcular_exato_continua_sem_aproximar():
    assert precos.calcular("claude-opus-4-1", {"in": 1000}, precos.FABRICA) == (0.0, False)
    assert precos.calcular("claude-opus-4-1", {"in": 1_000_000}, precos.FABRICA, aproximar=True) == (15.0, True)


# ── 3. Instagram ─────────────────────────────────────────────────────────
def test_instagram_versao_do_esquema_e_banco_antigo(tmp_path):
    caminho = tmp_path / "ig.db"
    with sqlite3.connect(caminho) as db:  # banco "antigo": sem versão e com dois próprios
        db.executescript(armazenar.SCHEMA)
        db.execute("INSERT INTO perfil VALUES ('a', 1, 1), ('b', 2, 1)")
    arm = Armazem(caminho)
    with sqlite3.connect(caminho) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == armazenar.VERSAO_ESQUEMA
        assert db.execute("SELECT COUNT(*) FROM perfil WHERE proprio = 1").fetchone()[0] == 1
        db.execute("PRAGMA user_version = 99")  # banco de versão mais nova: tolerado, não rebaixa
    Armazem(caminho)
    with sqlite3.connect(caminho) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 99
    assert arm.seguidores() == {"a": 1, "b": 2}


def test_definir_perfis_garante_um_unico_proprio(tmp_path):
    arm = Armazem(tmp_path / "ig.db")
    arm.definir_perfis({"a": 10, "b": 20}, proprio="a")
    arm.definir_perfis({"b": None}, proprio="b")
    with sqlite3.connect(arm.path) as db:
        assert [r[0] for r in db.execute("SELECT arroba FROM perfil WHERE proprio = 1")] == ["b"]
        assert db.execute("SELECT COUNT(*) FROM perfil").fetchone()[0] == 2  # ninguém foi apagado pelo REPLACE
    assert arm.seguidores() == {"a": 10, "b": 20}
    arm.definir_perfis({"c": 5})  # sem próprio informado: não mexe nos demais
    assert arm.seguidores()["c"] == 5


def test_rodada_para_importar_fronteira_de_semana(tmp_path):
    arm = Armazem(tmp_path / "ig.db")
    seg = datetime(2026, 10, 19, 10)  # segunda
    r1 = arm.rodada_para_importar(seg)
    assert arm.rodada_para_importar(seg + timedelta(days=6, hours=13)) == r1  # domingo, mesma semana ISO
    assert arm.rodada_para_importar(seg + timedelta(days=7)) != r1  # segunda seguinte
    assert arm.rodada_para_importar(seg, nova=True) != r1


def test_rodada_para_importar_concorrente_cria_uma_so(tmp_path):
    arm = Armazem(tmp_path / "ig.db")
    agora = datetime(2026, 10, 20, 9)
    ids, erros = [], []

    def tarefa():
        try:
            ids.append(arm.rodada_para_importar(agora))
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    fios = [threading.Thread(target=tarefa) for _ in range(8)]
    [f.start() for f in fios]
    [f.join() for f in fios]
    assert not erros and len(set(ids)) == 1 and len(arm.rodadas()) == 1


# ── 4. fusos reais ───────────────────────────────────────────────────────
def test_tz_resolve_zoneinfo_real_e_cai_no_fixo_se_faltar():
    assert isinstance(tz.resolver("America/New_York"), zoneinfo.ZoneInfo)
    assert tz.resolver("Brasilia Standard Time").utcoffset(datetime(2026, 1, 1)) == timedelta(hours=-3)
    assert tz.resolver("Mundo/Inexistente") is None


def test_tz_sem_banco_de_fusos_usa_deslocamento_fixo(monkeypatch):
    def faltando(nome):
        raise zoneinfo.ZoneInfoNotFoundError(nome)

    monkeypatch.setattr(zoneinfo, "ZoneInfo", faltando)
    assert tz.resolver("America/Sao_Paulo").utcoffset(None) == timedelta(hours=-3)
    assert tz.resolver("America/New_York") is None


def test_rrule_diaria_atravessa_o_horario_de_verao():
    zona = zoneinfo.ZoneInfo("America/New_York")
    texto = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nUID:1\r\nDTSTART;TZID=America/New_York:20260307T090000\r\n"
             "RRULE:FREQ=DAILY;COUNT=3\r\nSUMMARY:x\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
    achadas = ocorrencias.ocorrencias(ics.ler(texto), datetime(2026, 3, 1, tzinfo=zona), datetime(2026, 3, 20, tzinfo=zona), zona)
    assert [o.inicio.strftime("%d %H:%M") for o in achadas] == ["07 09:00", "08 09:00", "09 09:00"]  # hora de parede fixa
    assert [int(o.inicio.utcoffset().total_seconds() // 3600) for o in achadas] == [-5, -4, -4]  # troca em 8/3


# ── 5. aviso de rede do celular ──────────────────────────────────────────
def _ponte(modo, url, ativo=True):
    from jarvis.ui.api_mobile import MobileMixin

    class Ponte(MobileMixin):
        def __init__(self):
            self._mobile = type("S", (), {"ativo": ativo, "url": url})()
            self._pareamento = type("P", (), {"listar": lambda s: []})()
            self.mobile_modo = modo

    return Ponte()


@pytest.mark.parametrize("modo,url,ativo,tem_aviso", [
    ("rede", "http://192.168.0.5:8765", True, True),
    ("rede", "https://pc.local:8765", True, False),
    ("tailscale", "https://pc.ts.net:8765", True, False),
    ("local", "http://127.0.0.1:8765", True, False),
    ("rede", "", False, False),
])
def test_aviso_rede_so_para_http_na_lan(monkeypatch, modo, url, ativo, tem_aviso):
    monkeypatch.setattr("jarvis.config.load", lambda: Config())
    status = _ponte(modo, url, ativo).mobile_status()
    assert bool(status["aviso_rede"]) is tem_aviso
    if tem_aviso:
        assert "Tailscale" in status["aviso_rede"] and len(status["aviso_rede"]) < 200
