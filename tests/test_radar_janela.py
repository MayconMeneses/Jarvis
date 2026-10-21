import types

import pytest

from jarvis import config
from jarvis.brains.router import Router
from jarvis.chat import Conversation
from jarvis.config import Config
from jarvis.memory_db import MemoryDB
from jarvis.radar import servico
from jarvis.radar.ajustes import RadarConfig
from jarvis.radar.historico import Historico
from jarvis.radar.modelos import Fonte
from jarvis.ui import web


@pytest.fixture
def api(tmp_path, monkeypatch):
    pytest.importorskip("webview")
    from jarvis.ui import api_radar
    from jarvis.ui.api import Api

    cfg = Config()
    cfg.radar = RadarConfig(nicho="economia", pasta=str(tmp_path / "saida"))
    guardado = {"cfg": cfg}
    monkeypatch.setattr(config, "load", lambda path=None: guardado["cfg"])
    monkeypatch.setattr(config, "save", lambda c, path=None: guardado.update(cfg=c))
    monkeypatch.setattr(servico, "memory_db", types.SimpleNamespace(open_memory=lambda c=None: MemoryDB(tmp_path / "memoria.db")))
    historico = Historico(tmp_path / "radar.db")
    for modulo in (api_radar, servico):
        monkeypatch.setattr(modulo, "Historico", lambda: historico)
    monkeypatch.setattr(historico, "fechar", lambda: None)
    instance = Api(Config(), Conversation(Router([types.SimpleNamespace(name="x", ask=lambda m, s: None)]), "s"))
    instance._memory = MemoryDB(tmp_path / "memoria2.db")
    instance.guardado, instance.historico = guardado, historico
    yield instance
    servico.registrar(None)


def test_state_reports_config_sources_and_last_run(api):
    api.historico.salvar_fonte(Fonte("G1", "https://g1.globo.com/rss", nota=8))
    api.historico.registrar_execucao("2026-10-20", 1.0, 40, 12, 7, [], "PASS")
    s = api.radar_estado()
    assert s["nicho"] == "economia" and s["hora"] == "07:00" and s["ativo"] is False and s["usar_ia"] is False
    assert s["fontes"][0]["nome"] == "G1" and s["ultima"]["escolhidos"] == 7 and s["rodando"] is False and s["ia_disponivel"] is True


def test_save_validates_fields_and_ignores_unknown_ones(api):
    assert api.radar_salvar({"hora": "9:30", "ativo": True, "audio": False, "dias_uteis": False, "usar_ia": True}) == {"ok": True}
    r = api.guardado["cfg"].radar
    assert (r.hora, r.ativo, r.audio, r.dias_uteis, r.usar_ia) == ("09:30", True, False, False, True)
    api.radar_salvar({"hora": "99:99", "palavras_chave": ["hack"], "bloqueios": [], "ler_artigos": 999})
    r = api.guardado["cfg"].radar
    assert r.hora == "07:00" and r.palavras_chave == [] and r.ler_artigos == 3  # só os campos da janela mudam
    assert api.radar_salvar("lixo") == {"error": "dados inválidos"}


def test_turning_on_without_niche_is_refused_and_niche_change_seeds_sources(api):
    api.guardado["cfg"].radar.nicho = ""
    assert "Defina o nicho" in api.radar_salvar({"ativo": True})["error"] and api.guardado["cfg"].radar.ativo is False
    assert api.radar_salvar({"nicho": "inteligência artificial na saúde"}) == {"ok": True}
    r = api.guardado["cfg"].radar
    assert r.nicho == "inteligência artificial na saúde" and "inteligencia" in r.palavras_chave and api.historico.fontes()


def test_source_toggle_add_and_commands_go_through_the_same_service(api):
    api.historico.salvar_fonte(Fonte("G1", "https://g1.globo.com/rss", nota=8))
    assert api.radar_fonte_ativar("G1", False) == {"ok": True} and api.radar_estado()["fontes"][0]["ativa"] is False
    assert "Diga o endereço" in api.radar_fonte_adicionar("  ")["text"]
    assert "Defina o nicho primeiro" in (lambda c: (setattr(c.radar, "nicho", ""), api.radar_rodar())[1])(api.guardado["cfg"])["text"]
    assert "Ainda não há áudio" in api.radar_ouvir()["text"] and "Ainda não há boletim" in api.radar_abrir()["text"]


def test_page_contains_the_radar_panel_and_scripts():
    pagina = web.page()
    assert 'id="open-radar"' in pagina and 'id="radar"' in pagina and "radar_estado" in pagina and "#radar-fontes" in pagina
    for id_ in ("radar-nicho", "radar-hora", "radar-ativo", "radar-uteis", "radar-ia", "radar-audio", "radar-gerar", "radar-ouvir", "radar-abrir"):
        assert f'id="{id_}"' in pagina
