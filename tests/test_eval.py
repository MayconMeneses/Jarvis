import json

import numpy as np
import pytest

from jarvis.eval import bench, metrics, quality


# ── BLEU ─────────────────────────────────────────────────────────────────

def test_bleu_identical_is_one_and_disjoint_is_zero():
    ref = "o gato está embaixo da cama"
    assert metrics.bleu(ref, ref) == pytest.approx(1.0)
    assert metrics.bleu("chove muito hoje lá fora", ref) == 0.0


def test_bleu_uses_best_of_multiple_references_and_brevity_penalty():
    refs = ["a casa é azul e bonita", "a casa azul é bonita"]
    assert metrics.bleu("a casa azul é bonita", refs) == pytest.approx(1.0)
    # Candidato sem 3- e 4-gramas: BLEU padrão é 0 (mesmo comportamento do NLTK).
    assert metrics.bleu("a casa", "a casa é azul e bonita") == 0.0
    shorter = metrics.bleu("a casa é azul", "a casa é azul e bonita")
    assert 0 < shorter < 1  # todos os n-gramas casam, mas a penalidade de brevidade reduz


# ── ROUGE (exemplo clássico de Lin, 2004) ────────────────────────────────

def test_rouge_known_values():
    cand, ref = "the cat was found under the bed", "the cat was under the bed"
    r1 = metrics.rouge_n(cand, ref, 1)
    assert r1["precisao"] == pytest.approx(6 / 7) and r1["recall"] == pytest.approx(1.0)
    r2 = metrics.rouge_n(cand, ref, 2)
    assert r2["precisao"] == pytest.approx(4 / 6) and r2["recall"] == pytest.approx(4 / 5)
    rl = metrics.rouge_l(cand, ref)
    assert rl["precisao"] == pytest.approx(6 / 7) and rl["recall"] == pytest.approx(1.0)
    assert rl["f1"] == pytest.approx(2 * (6 / 7) / (6 / 7 + 1))


# ── METEOR ───────────────────────────────────────────────────────────────

def test_meteor_identical_near_one_and_stems_count():
    ref = "eu gosto de programação em python"
    assert metrics.meteor(ref, ref) == pytest.approx(1 - 0.5 * (1 / 6) ** 3)
    exact_only = metrics.meteor("eu gosto de música em python", ref)
    with_stem = metrics.meteor("eu gosto de programar em python", ref)  # programar ~ programação
    assert with_stem > exact_only


def test_meteor_penalizes_scrambled_order():
    ref = "a jarvis abre o navegador agora"
    assert metrics.meteor("agora o navegador abre a jarvis", ref) < metrics.meteor(ref, ref)


# ── BERTScore (com codificador falso e determinístico) ───────────────────

class FakeEncoder:
    """Cada palavra vira um vetor fixo: mesma palavra = cosseno 1, palavras diferentes ~ 0."""

    def token_embeddings(self, text):
        words = metrics.tokens(text)
        rng = np.random.default_rng(0)
        table = {w: rng.standard_normal(64) for w in sorted(set(words) | {"x"})}
        vectors = np.array([table[w] / np.linalg.norm(table[w]) for w in words]) if words else np.zeros((0, 64))
        return vectors

    def similarity(self, a, b):
        wa, wb = set(metrics.tokens(a)), set(metrics.tokens(b))
        return len(wa & wb) / max(1, len(wa | wb))


def test_bertscore_precision_recall_f1():
    enc = FakeEncoder()
    same = metrics.bertscore("docker cria containers", "docker cria containers", enc)
    assert same["f1"] == pytest.approx(1.0)
    partial = metrics.bertscore("docker cria", "docker cria containers isolados", enc)
    assert partial["precisao"] == pytest.approx(1.0) and partial["recall"] < 1.0


# ── classificação ────────────────────────────────────────────────────────

def test_classification_report_per_class_macro_micro():
    expected = ["a", "a", "b", "b", "c"]
    predicted = ["a", "b", "b", "b", "a"]
    r = metrics.classification_report(expected, predicted)
    assert r["por_classe"]["a"] == {"precisao": 0.5, "recall": 0.5, "f1": 0.5, "suporte": 2}
    assert r["por_classe"]["b"]["precisao"] == pytest.approx(2 / 3) and r["por_classe"]["b"]["recall"] == 1.0
    assert r["por_classe"]["c"]["f1"] == 0.0
    assert r["acuracia"] == pytest.approx(3 / 5) and r["micro"]["f1"] == pytest.approx(3 / 5)
    assert r["confusao"]["c"] == {"a": 1}


# ── critérios de qualidade ───────────────────────────────────────────────

def test_clarity_penalizes_very_long_sentences():
    short = "A RAM está em 90%. Feche o Chrome para liberar memória."
    long = " ".join(["a memória do computador está sendo usada"] * 8) + "."
    assert quality.clarity(short)[0] > quality.clarity(long)[0]


def test_fluency_penalizes_repetition():
    good = "O Docker empacota aplicações em contêineres leves e portáteis para qualquer servidor."
    bad = "o docker é bom o docker é bom o docker é bom o docker é bom o docker é bom."
    assert quality.fluency(good)[0] > quality.fluency(bad)[0]


def test_fidelity_checks_support_in_sources():
    sources = ["Python foi criado por Guido van Rossum e lançado em 1991."]
    supported = quality.fidelity("Python foi criado por Guido van Rossum.", sources)
    invented = quality.fidelity("Python foi criado pela Microsoft em 2005 para jogos.", sources)
    assert supported[0] == 10.0 and invented[0] == 0.0
    assert quality.fidelity("qualquer coisa aqui", [])[0] is None


def test_relevance_by_keywords_without_model():
    q = "qual a capital da Austrália?"
    assert quality.relevance(q, "A capital da Austrália é Camberra.")[0] > quality.relevance(q, "Hoje vai chover.")[0]


def test_evaluate_returns_all_criteria_and_average():
    result = quality.evaluate("o que é docker?", "Docker é uma plataforma de contêineres. Ela isola aplicações.")
    assert set(result["notas"]) == {"coerencia", "clareza", "relevancia", "fidelidade", "fluidez"}
    assert result["notas"]["fidelidade"] is None and 0 <= result["media"] <= 10


# ── benchmarks ───────────────────────────────────────────────────────────

def test_typo_perturbation_is_deterministic():
    assert bench._typo("como está o computador") == bench._typo("como está o computador")
    assert bench._typo("como está o computador") != "como está o computador"


def test_command_benchmark_reports_training_and_held_out_sets():
    from jarvis.local.engine import LocalEngine

    result = bench.bench_commands(LocalEngine(load_config=lambda: None, brave_key=lambda: None))
    assert result["total"] >= 60 and result["total_validacao"] >= 30
    assert result["relatorio"]["acuracia"] >= 0.9 and result["validacao"]["acuracia"] >= 0.85
    assert set(result["robustez"]) == set(bench.PERTURBATIONS)


def test_summary_benchmark_compares_with_lead2_baseline():
    result = bench.bench_summaries(encoder=None)
    assert set(result["metricas"]) == {"Jarvis (extrativo)", "baseline Lead-2"}
    assert {"bleu", "rouge1", "rouge2", "rougeL", "meteor"} <= set(result["metricas"]["baseline Lead-2"])
    assert result["qualidade"]["fidelidade"] == 10.0  # extrativo: tudo vem do texto


def test_judge_parses_rubric_json():
    from jarvis.brains.base import Answer

    class Judge:
        name = "claude"

        def ask(self, messages, system):
            return Answer('Notas: {"coerencia": 9, "clareza": 8, "relevancia": 10, "fidelidade": 7, "fluidez": 9}', "claude")

    scores = bench.judge_answer(Judge(), "p", "r", "ref")
    assert scores == {"coerencia": 9.0, "clareza": 8.0, "relevancia": 10.0, "fidelidade": 7.0, "fluidez": 9.0}


def test_every_answer_gets_quality_and_is_logged(tmp_path, monkeypatch):
    pytest.importorskip("webview")
    from jarvis import config
    from jarvis.brains.base import Answer
    from jarvis.brains.router import Router
    from jarvis.chat import Conversation
    from jarvis.ui.app import Api

    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)

    class Brain:
        name = "claude"

        def ask(self, messages, system):
            return Answer("A capital da Austrália é Camberra.", "claude")

    api = Api(config.Config(), Conversation(Router([Brain()]), "s"))
    res = api.send("qual a capital da Austrália?")
    assert 0 <= res["qualidade"]["media"] <= 10
    record = json.loads((tmp_path / "avaliacoes.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert record["cerebro"] == "claude" and record["media"] == res["qualidade"]["media"]


# ── motor local mais robusto ─────────────────────────────────────────────

@pytest.mark.parametrize("text,intent", [
    ("por favor, abre o WhatsApp", "abrir"), ("você pode abrir o chrome", "abrir"),
    ("como está o comptuador", "pc"), ("que horsa são", "hora"),
    ("busque informações sobre Docker", "pesquisa"),
])
def test_polite_prefixes_and_typos_are_understood(text, intent):
    from jarvis.local.engine import LocalEngine

    assert LocalEngine(load_config=lambda: None, brave_key=lambda: None).classify(text)[0] == intent


def test_mentioning_jobs_is_not_a_job_search():
    from jarvis.local.engine import LocalEngine

    engine = LocalEngine(load_config=lambda: None, brave_key=lambda: None)
    assert engine.classify("lembre que eu prefiro vagas remotas") is None
    assert engine.classify("tem vagas de python?")[0] == "vagas"
