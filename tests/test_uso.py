"""Módulo de uso de IA: coletor de .jsonl (sintético), preços, cota, orçamento, exportação e agentes."""

import json
import time
from datetime import datetime

import pytest

from jarvis.uso import agentes, coletor_claude, configuracao, cota, exportar, orcamento, precos, resumo
from jarvis.uso.registro import Registro

AGORA = datetime(2026, 10, 20, 15, 0, 0).timestamp()


def linha(msg_id, req, out, *, modelo="claude-opus-5-5", ts=AGORA - 60, sessao="s1", cwd="C:\\x\\proj", side=False, cin=10, cw=100, cr=1000, texto="SEGREDO"):
    iso = datetime.fromtimestamp(ts).astimezone().isoformat()
    return json.dumps({"type": "assistant", "timestamp": iso, "sessionId": sessao, "cwd": cwd, "isSidechain": side, "requestId": req,
                       "message": {"id": msg_id, "model": modelo, "content": [{"type": "text", "text": texto}],
                                   "usage": {"input_tokens": cin, "output_tokens": out, "cache_creation_input_tokens": cw,
                                             "cache_read_input_tokens": cr, "cache_creation": {"ephemeral_1h_input_tokens": cw}}}}) + "\n"


@pytest.fixture
def reg(tmp_path):
    r = Registro(tmp_path / "uso.db")
    yield r
    r.fechar()


@pytest.fixture
def raiz(tmp_path):
    pasta = tmp_path / "projects" / "C--x-proj"
    (pasta / "s1" / "subagents").mkdir(parents=True)
    return tmp_path / "projects"


def escrever(raiz, nome, *linhas):
    arq = raiz / "C--x-proj" / nome
    with open(arq, "a", encoding="utf-8") as f:
        f.writelines(linhas)
    return arq


def test_deduplica_por_mensagem_e_pedido_e_ignora_synthetic(reg, raiz):
    escrever(raiz, "s1.jsonl", linha("m1", "r1", 5), linha("m1", "r1", 50), linha("m1", "r1", 20), linha("m2", "r2", 7, modelo="<synthetic>"))
    coletor_claude.coletar(reg, raiz)
    linhas = reg.linhas()
    assert len(linhas) == 1 and linhas[0]["tout"] == 50 and linhas[0]["projeto"] == "proj"


def test_incremental_nao_relê_nem_duplica_e_espera_linha_completa(reg, raiz):
    arq = escrever(raiz, "s1.jsonl", linha("m1", "r1", 5))
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 1
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 0
    parcial = linha("m2", "r2", 9)
    with open(arq, "a", encoding="utf-8") as f:
        f.write(parcial[:40])  # linha ainda sendo escrita
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 0
    with open(arq, "a", encoding="utf-8") as f:
        f.write(parcial[40:])
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 1
    assert len(reg.linhas()) == 2


def test_subagente_por_pasta_ou_flag_e_nao_guarda_conteudo(reg, raiz, tmp_path):
    escrever(raiz, "s1/subagents/a.jsonl", linha("m1", "r1", 5, sessao="s1"))
    escrever(raiz, "s1.jsonl", linha("m2", "r2", 5, side=True), linha("m3", "r3", 5))
    coletor_claude.coletar(reg, raiz)
    assert sorted(l["sub"] for l in reg.linhas()) == [0, 1, 1]
    reg.fechar()
    assert b"SEGREDO" not in (tmp_path / "uso.db").read_bytes()


def test_arquivo_estranho_nao_derruba(reg, raiz):
    escrever(raiz, "s1.jsonl", "lixo{{{\n", '{"message": {"usage": 3}}\n', linha("m1", "r1", 5))
    assert coletor_claude.coletar(reg, raiz)["linhas"] == 1
    assert coletor_claude.coletar(reg, raiz / "nao-existe") == {"arquivos": 0, "linhas": 0}


def test_precos_calculo_e_modelo_sem_preco(tmp_path):
    tab = precos.carregar(tmp_path / "p.json")
    uso = {"in": 1_000_000, "out": 1_000_000, "cw": 1_000_000, "cw1h": 1_000_000, "cr": 1_000_000}
    custo, ok = precos.calcular("claude-opus-5-5", uso, tab)
    assert ok and custo == pytest.approx(15 + 75 + 30 + 1.5)
    assert precos.calcular("claude-sonnet-5", uso, tab) == (0.0, False)  # id sem sufixo: não existe na tabela
    assert precos.calcular("claude-fable-5-1", uso, tab)[1] is False  # id da casa, ainda sem preço
    assert precos.calcular("claude-opus-5-5-20261001[1m]", uso, tab)[1] is True


def test_precos_salvar_valida(tmp_path):
    caminho = tmp_path / "p.json"
    salvo = precos.salvar({"modelos": {"X-1": {"in": "2,5", "out": "-1"}, "": {"in": 1, "out": 1}}}, caminho)
    assert salvo["modelos"] == {"x-1": {"in": 2.5, "out": None}}
    assert precos.carregar(caminho)["modelos"]["x-1"]["in"] == 2.5


def test_custo_sem_preco_e_destacado_no_resumo(reg):
    reg.inserir(ts=AGORA - 10, fonte="jsonl", provedor="claude", modelo="claude-sonnet-5", uso={"in": 5, "out": 5, "cw": 0, "cw1h": 0, "cr": 0}, chave="a|b")
    r = resumo.resumo(reg, "hoje", AGORA)
    assert r["sem_preco"] == ["claude-sonnet-5"] and r["por_modelo"][0]["preco_ok"] is False


def test_provedores_gratis_custam_zero_e_local_conta_economia(reg):
    reg.ao_vivo("gemini", "gemini-x", {"in": 100, "out": 50}, ts=AGORA - 5)
    reg.ao_vivo("local", "", None, ts=AGORA - 4)
    r = resumo.resumo(reg, "hoje", AGORA)
    assert r["totais"]["custo"] == 0 and r["locais"] == {"local": 1, "ia": 1, "pct_local": 50.0}


def test_cota_janela_5h_semana_e_calibracao(reg):
    for i, off in enumerate((9 * 3600, 4 * 3600, 3 * 3600)):  # a 1a janela (9 h atras) ja acabou; a 2a abriu ha 4 h
        reg.inserir(ts=AGORA - off, fonte="jsonl", provedor="claude", modelo="m", uso={"in": 100, "out": 100, "cw": 0, "cw1h": 0, "cr": 0}, chave=f"k{i}")
    e = cota.estado(reg, AGORA)
    assert e["janela_5h"]["msgs"] == 2 and e["janela_5h"]["usado"] == 400 and e["janela_5h"]["pct"] is None
    assert cota.calibrar(reg, AGORA, "5h", 80)["teto"] == 500
    e = cota.estado(reg, AGORA)
    assert e["janela_5h"]["pct"] == 80 and e["janela_5h"]["alerta"] is True
    with pytest.raises(ValueError):
        cota.calibrar(reg, AGORA, "ano", 50)


def test_cota_acaba_antes_do_reset(reg):
    configuracao.salvar(reg, {"teto_5h": 1000})
    reg.inserir(ts=AGORA - 3600, fonte="jsonl", provedor="claude", modelo="m", uso={"in": 0, "out": 600, "cw": 0, "cw1h": 0, "cr": 0}, chave="a")
    m = cota.estado(reg, AGORA)["janela_5h"]  # 600 em 1 h: em 5 h seriam 3000 > 1000
    assert m["acaba_antes_do_reset"] and m["acaba_em"] > AGORA


def test_orcamento_projecao_e_alerta(reg):
    configuracao.salvar(reg, {"orcamento_mensal": 100, "alerta_pct": 80})
    reg.inserir(ts=AGORA - 3600, fonte="ao_vivo", provedor="claude", modelo="m", custo_rep=85.0)
    o = orcamento.mes(reg, AGORA)
    assert o["gasto"] == 85 and o["alerta"] and o["projecao_estoura"] and o["pct"] == 85


def test_configuracao_rejeita_valores_ruins(reg):
    c = configuracao.salvar(reg, {"teto_5h": "abc", "alerta_pct": 500, "unidade": "x", "semana_dow": 9})
    assert c["teto_5h"] is None and c["alerta_pct"] == 100 and c["unidade"] == "tokens" and c["semana_dow"] == 2


def test_exportar_importar_e_csv_sem_injecao(reg, tmp_path, monkeypatch):
    reg.inserir(ts=AGORA - 5, fonte="jsonl", provedor="claude", modelo="=cmd", projeto="p", sessao="s", uso={"in": 1, "out": 2, "cw": 0, "cw1h": 0, "cr": 0}, chave="x|y")
    texto = exportar.exportar_json(reg)
    outro = Registro(tmp_path / "outro.db")
    assert exportar.importar_json(outro, texto)["linhas"] == 1
    exportar.importar_json(outro, texto)  # repetir não duplica
    assert len(outro.linhas()) == 1
    assert "'=cmd" in exportar.exportar_csv(reg)
    for ruim in ("nao json", "[]", '{"linhas": 3}'):
        with pytest.raises(ValueError):
            exportar.importar_json(outro, ruim)
    outro.fechar()


def test_uso_por_sessao_contrato_e_subagentes(reg):
    reg.inserir(ts=AGORA - 5, fonte="jsonl", provedor="claude", modelo="claude-opus-5-5", sessao="abc", uso={"in": 1, "out": 2, "cw": 3, "cw1h": 0, "cr": 4}, chave="1|1")
    reg.inserir(ts=AGORA - 4, fonte="jsonl", provedor="claude", modelo="claude-opus-5-5", sessao="abc", sub=True, uso={"in": 1, "out": 1, "cw": 0, "cw1h": 0, "cr": 0}, chave="2|2")
    u = agentes.uso_por_sessao("abc", reg)
    assert {"tokens_in", "tokens_out", "cache", "custo_usd", "estimado", "origem"} <= set(u)
    assert (u["tokens_in"], u["tokens_out"], u["cache"], u["origem"], u["estimado"]) == (2, 3, 7, "jsonl", True)
    assert u["subagentes"]["tokens_out"] == 1
    assert agentes.uso_por_sessao("nada", reg)["origem"] == "nenhum"
    assert agentes.uso_agentes(["abc", "z"], reg)["z"]["origem"] == "nenhum"
    assert time.time() > 0
