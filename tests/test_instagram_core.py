"""Núcleo do analista de Instagram: fórmulas e fronteiras. Os casos vêm de tests/dados/instagram_casos.json,
o MESMO arquivo que o teste do celular (movel/testes/instagram.test.mjs) lê: a lógica precisa ser idêntica."""

import json
from pathlib import Path

import pytest

from jarvis.instagram import analise, ganchos, higiene, importar, metricas

CASOS = json.loads((Path(__file__).parent / "dados" / "instagram_casos.json").read_text(encoding="utf-8"))
epoch = higiene.epoch


@pytest.mark.parametrize("texto,esperado", CASOS["numeros"])
def test_numeros(texto, esperado):
    assert importar.numero(texto) == esperado


@pytest.mark.parametrize("texto,esperado", CASOS["datas"])
def test_datas(texto, esperado):
    assert epoch(texto) == esperado


def test_post_de_47h_e_imaturo_e_de_48h_49h_sao_maduros():
    agora = epoch(CASOS["maturidade"]["agora"])
    for data, esperado in CASOS["maturidade"]["itens"]:
        assert higiene.maturidade({"data": data}, agora) == esperado


@pytest.mark.parametrize("n,esperado", CASOS["confianca"])
def test_perfil_com_5_posts_tem_baixa_confianca_e_com_6_nao(n, esperado):
    assert higiene.confianca(n) == esperado


@pytest.mark.parametrize("valores,esperado", CASOS["medianas"])
def test_mediana_par_impar_vazia(valores, esperado):
    assert metricas.mediana(valores) == esperado


@pytest.mark.parametrize("legenda,esperado", CASOS["ganchos"])
def test_ganchos(legenda, esperado):
    assert ganchos.classificar_gancho(legenda) == esperado


@pytest.mark.parametrize("legenda,esperado", CASOS["cta"])
def test_cta(legenda, esperado):
    assert ganchos.tem_cta_comentario(legenda) is esperado


@pytest.mark.parametrize("caso", CASOS["engajamento"])
def test_engajamento(caso):
    assert metricas.engajamento(caso["post"], caso["pesos"]) == caso["valor"]


def test_engajamento_avisa_o_peso_ignorado_e_likes_ocultos_nunca_viram_zero():
    valor, motivo = metricas.engajamento_detalhe({"likes": 10, "comentarios": None})
    assert valor == 10 and "peso ignorado" in motivo
    assert metricas.engajamento_detalhe({"likes": None}) == (None, "likes ocultos")


@pytest.mark.parametrize("caso", CASOS["comment_rate"])
def test_comment_rate_e_selos_nas_fronteiras(caso):
    taxa, _ = metricas.comment_rate(caso)
    assert (taxa is None and caso["taxa"] is None) or abs(taxa - caso["taxa"]) < 1e-9
    assert metricas.badge(caso) == caso["badge"]


@pytest.mark.parametrize("caso", CASOS["outlier"])
def test_outlier_exatamente_2_e_amostras_pequenas(caso):
    score, motivo = metricas.outlier_score(caso["eng"], caso["grupo"])
    assert (score is None and caso["score"] is None) or abs(score - caso["score"]) < 1e-9
    assert metricas.eh_outlier(score) is caso["outlier"]
    assert (score is not None) or motivo


def test_faixas_por_tercis():
    f = CASOS["faixas"]
    cortes = metricas.cortes_tercis(f["razoes"])
    assert cortes == pytest.approx(f["cortes"])
    for valor, faixa in f["faixas"]:
        assert metricas.faixa_alcance(valor, cortes) == faixa
    assert metricas.cortes_tercis(f["poucas"][0]) is None
    assert metricas.alcance_relativo(None, 100)[0] is None and metricas.alcance_relativo(10, 0)[0] is None


def test_analise_completa_igual_ao_esperado_e_ranking_prioriza_maior_alcance():
    c = CASOS["analise"]
    r = analise.analisar(c["posts"], c["seguidores"], None, epoch(c["agora"]))
    e = c["esperado"]
    assert r["ranking"] == e["ranking"] and r["ranking_por"] == "alcance"
    assert [p["id"] for p in r["posts"] if p["outlier"]] == e["outliers"]
    assert [p["id"] for p in r["posts"] if p["imaturo"]] == e["imaturos"]
    assert {p["id"]: p["faixa"] for p in r["posts"] if p["faixa"]} == e["faixas"]
    assert {p["id"]: p["gancho"] for p in r["posts"]} == e["ganchos"]
    assert r["grupos"] == e["grupos"]
    assert {a: p["confianca"] for a, p in r["perfis"].items()} == e["confianca"]
    assert r["formatos"][0]["formato"] == e["formato_vencedor"]
    assert [g["gancho"] for g in r["ganchos"]] == e["ordem_ganchos"]


def test_posts_imaturos_nao_entram_nas_medianas():
    c = CASOS["analise"]
    r = analise.analisar(c["posts"], c["seguidores"], None, epoch(c["agora"]))
    assert r["grupos"][0]["n"] == 4
