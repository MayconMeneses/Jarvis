"""Benchmarks reproduzíveis da Jarvis.

1. Comandos do modo independente: precisão, recall e F1 por intenção (conjunto rotulado).
2. Robustez: a mesma bateria com perturbações (sem acento, maiúsculas, erro de digitação,
   cortesia e ruído no fim) e a queda de acurácia em cada uma.
3. Resumos extrativos (pesquisa sem IA): BLEU, ROUGE-1/2/L, METEOR e BERTScore contra
   resumos de referência, comparados ao baseline Lead-2 (duas primeiras frases).
4. Respostas dos cérebros (opcional, gasta limite): as mesmas métricas + latência +
   critérios de qualidade, por cérebro (Claude, Gemini, local).
5. Juiz por rubrica (opcional, substitui o BLEURT, que não roda neste PC).
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

from jarvis.eval import metrics, quality

DATA = Path(__file__).with_name("data")


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# ── 1 e 2: comandos e robustez ───────────────────────────────────────────

def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def _typo(text: str) -> str:
    """Troca duas letras do meio da palavra mais longa (erro de digitação determinístico)."""
    words = text.split()
    if not words:
        return text
    i = max(range(len(words)), key=lambda k: len(words[k]))
    w = words[i]
    if len(w) >= 5:
        m = len(w) // 2
        words[i] = w[:m - 1] + w[m] + w[m - 1] + w[m + 1:]
    return " ".join(words)


PERTURBATIONS = {
    "original": lambda t: t,
    "sem acentos": _strip_accents,
    "MAIÚSCULAS": str.upper,
    "erro de digitação": _typo,
    "cortesia (por favor)": lambda t: "por favor, " + t[0].lower() + t[1:],
    "ruído no fim": lambda t: t.rstrip("?!.") + " agora mesmo",
}


def predict(engine, text: str) -> str:
    found = engine.classify(text)
    return found[0] if found else "nenhum"


def bench_commands(engine) -> dict:
    """Bateria de ajuste (usada para escrever as regras) + validação (nunca usada para ajustar).

    A diferença entre as duas mostra o quanto as regras "decoraram" a bateria (overfitting).
    """
    data = load("comandos.json")
    expected = [label for _, label in data]
    report = metrics.classification_report(expected, [predict(engine, t) for t, _ in data])
    robustness = {}
    for name, change in PERTURBATIONS.items():
        predicted = [predict(engine, change(t)) for t, _ in data]
        robustness[name] = sum(p == e for p, e in zip(predicted, expected)) / len(expected)
    errors = [(t, e, predict(engine, t)) for t, e in data if predict(engine, t) != e]
    held_out = load("comandos_validacao.json")
    validation = metrics.classification_report([l for _, l in held_out], [predict(engine, t) for t, _ in held_out])
    validation_errors = [(t, e, predict(engine, t)) for t, e in held_out if predict(engine, t) != e]
    return {"relatorio": report, "robustez": robustness, "erros": errors, "total": len(data),
            "validacao": validation, "erros_validacao": validation_errors, "total_validacao": len(held_out)}


# ── 3: resumos ───────────────────────────────────────────────────────────

def _text_scores(candidate: str, reference: str, encoder) -> dict:
    scores = {"bleu": metrics.bleu(candidate, reference), "meteor": metrics.meteor(candidate, reference)}
    for name, prf in metrics.rouge(candidate, reference).items():
        scores[name] = prf["f1"]
    if encoder is not None:
        scores["bertscore"] = metrics.bertscore(candidate, reference, encoder)["f1"]
    return scores


def _average(rows: list[dict]) -> dict:
    keys = rows[0].keys() if rows else []
    return {k: sum(r[k] for r in rows) / len(rows) for k in keys}


def bench_summaries(encoder=None) -> dict:
    from jarvis.local import websearch

    systems = {"Jarvis (extrativo)": [], "baseline Lead-2": []}
    qualities = []
    for item in load("resumos.json"):
        chosen = websearch.extract(item["pergunta"], [(1, item["texto"])], top=2)
        candidate = " ".join(s for s, _ in chosen)
        lead = " ".join(websearch.sentences(item["texto"])[:2])
        systems["Jarvis (extrativo)"].append(_text_scores(candidate, item["referencia"], encoder))
        systems["baseline Lead-2"].append(_text_scores(lead, item["referencia"], encoder))
        qualities.append(quality.evaluate(item["pergunta"], candidate, [item["texto"]], encoder)["notas"])
    return {"metricas": {name: _average(rows) for name, rows in systems.items()},
            "qualidade": _average([{k: v for k, v in q.items() if v is not None} for q in qualities]),
            "total": len(qualities)}


# ── 4 e 5: respostas dos cérebros e juiz ─────────────────────────────────

SYSTEM = "Você é a Jarvis. Responda em português (ou no idioma pedido), de forma direta e curta."


def bench_answers(brains: list, encoder=None, judge=None) -> dict:
    out = {}
    for brain in brains:
        rows, qualities, latencies, failures, judged = [], [], [], 0, []
        for item in load("respostas.json"):
            start = time.time()
            try:
                answer = brain.ask([{"role": "user", "content": item["pergunta"]}], SYSTEM).text
            except Exception:
                failures += 1
                continue
            latencies.append(time.time() - start)
            answer = re.sub(r"\n+_\(modo independente.*$", "", answer, flags=re.S)
            rows.append(_text_scores(answer, item["referencia"], encoder))
            qualities.append(quality.evaluate(item["pergunta"], answer, None, encoder)["notas"])
            if judge is not None:
                judged.append(judge_answer(judge, item["pergunta"], answer, item["referencia"]))
        out[brain.name] = {
            "metricas": _average(rows) if rows else {},
            "qualidade": _average([{k: v for k, v in q.items() if v is not None} for q in qualities]) if qualities else {},
            "latencia_media_s": sum(latencies) / len(latencies) if latencies else None,
            "falhas": failures,
            "juiz": _average([j for j in judged if j]) if any(judged) else {},
        }
    return out


RUBRIC = ("Avalie a RESPOSTA para a PERGUNTA, comparando com a REFERÊNCIA. Dê notas inteiras de 1 a 10 para "
          "coerencia, clareza, relevancia, fidelidade (à referência) e fluidez. Responda SOMENTE com JSON no "
          "formato {\"coerencia\": n, \"clareza\": n, \"relevancia\": n, \"fidelidade\": n, \"fluidez\": n}.")


def judge_answer(judge, question: str, answer: str, reference: str) -> dict | None:
    prompt = f"{RUBRIC}\n\nPERGUNTA: {question}\nREFERÊNCIA: {reference}\nRESPOSTA: {answer}"
    try:
        text = judge.ask([{"role": "user", "content": prompt}], "Você é um avaliador rigoroso e imparcial.").text
        data = json.loads(re.search(r"\{.*\}", text, re.S).group(0))
        return {k: float(data[k]) for k in ("coerencia", "clareza", "relevancia", "fidelidade", "fluidez")}
    except Exception:
        return None


def numeric_summary(commands: dict, summaries: dict) -> dict:
    """Números-chave (maior = melhor) para comparar uma versão com a anterior."""
    jarvis = summaries["metricas"]["Jarvis (extrativo)"]
    return {
        "comandos_acuracia": commands["relatorio"]["acuracia"],
        "comandos_f1_macro": commands["relatorio"]["macro"]["f1"],
        "validacao_acuracia": commands["validacao"]["acuracia"],
        "validacao_f1_macro": commands["validacao"]["macro"]["f1"],
        "robustez_media": sum(commands["robustez"].values()) / len(commands["robustez"]),
        "resumo_rougeL": jarvis["rougeL"],
        "resumo_meteor": jarvis["meteor"],
    }


# ── relatório ────────────────────────────────────────────────────────────

def _pct(v) -> str:
    return "—" if v is None else f"{v:.2f}"


def report_markdown(commands: dict | None, summaries: dict | None, answers: dict | None, semantic: bool) -> str:
    lines = [f"# Avaliação da Jarvis — {time.strftime('%d/%m/%Y %H:%M')}", ""]
    if not semantic:
        lines += ["> BERTScore e as notas semânticas foram pulados (modelo MiniLM não carregado).", ""]
    if commands:
        r = commands["relatorio"]
        lines += ["## 1. Comandos do modo independente (precisão, recall, F1)", "",
                  f"Acurácia **{r['acuracia']:.1%}** em {commands['total']} frases · F1 macro **{r['macro']['f1']:.2f}** · "
                  f"F1 micro **{r['micro']['f1']:.2f}**", "",
                  "| Intenção | Precisão | Recall | F1 | Suporte |", "|---|---|---|---|---|"]
        lines += [f"| {k} | {v['precisao']:.2f} | {v['recall']:.2f} | {v['f1']:.2f} | {v['suporte']} |"
                  for k, v in r["por_classe"].items()]
        v = commands["validacao"]
        gap = r["acuracia"] - v["acuracia"]
        lines += ["", f"**Validação (frases nunca usadas no ajuste):** acurácia **{v['acuracia']:.1%}** em "
                  f"{commands['total_validacao']} frases · F1 macro **{v['macro']['f1']:.2f}** · "
                  f"diferença ajuste−validação **{gap:+.1%}** "
                  f"({'sinal de overfitting' if gap > 0.05 else 'generaliza bem'})"]
        lines += [f"- erro na validação: \"{t}\" → esperado `{e}`, previsto `{p}`" for t, e, p in commands["erros_validacao"]]
        lines += ["", "## 2. Robustez (acurácia por perturbação)", "", "| Perturbação | Acurácia |", "|---|---|"]
        lines += [f"| {k} | {v:.1%} |" for k, v in commands["robustez"].items()]
        if commands["erros"]:
            lines += ["", "**Erros na bateria original:**"]
            lines += [f"- \"{t}\" → esperado `{e}`, previsto `{p}`" for t, e, p in commands["erros"]]
    if summaries:
        lines += ["", "## 3. Resumos extrativos (pesquisa sem IA)", "",
                  "| Sistema | BLEU | ROUGE-1 | ROUGE-2 | ROUGE-L | METEOR | BERTScore |", "|---|---|---|---|---|---|---|"]
        for name, m in summaries["metricas"].items():
            lines.append(f"| {name} | {m['bleu']:.2f} | {m['rouge1']:.2f} | {m['rouge2']:.2f} | {m['rougeL']:.2f} | "
                         f"{m['meteor']:.2f} | {_pct(m.get('bertscore'))} |")
        q = summaries["qualidade"]
        lines += ["", "Critérios (0–10) do resumo da Jarvis: " + " · ".join(f"{k} {v:.1f}" for k, v in q.items())]
    if answers:
        lines += ["", "## 4. Respostas por cérebro", "",
                  "| Cérebro | BLEU | ROUGE-L | METEOR | BERTScore | Qualidade (0–10) | Latência | Falhas |",
                  "|---|---|---|---|---|---|---|---|"]
        for name, a in answers.items():
            m, q = a["metricas"], a["qualidade"]
            avg_q = sum(q.values()) / len(q) if q else None
            lat = f"{a['latencia_media_s']:.1f}s" if a["latencia_media_s"] else "—"
            lines.append(f"| {name} | {_pct(m.get('bleu'))} | {_pct(m.get('rougeL'))} | {_pct(m.get('meteor'))} | "
                         f"{_pct(m.get('bertscore'))} | {_pct(avg_q)} | {lat} | {a['falhas']} |")
        judged = {n: a["juiz"] for n, a in answers.items() if a["juiz"]}
        if judged:
            lines += ["", "**Juiz por rubrica (1–10, substitui o BLEURT):**"]
            lines += [f"- {n}: " + " · ".join(f"{k} {v:.1f}" for k, v in j.items()) for n, j in judged.items()]
    lines += ["", "---", "Métricas: BLEU (Papineni 2002, suavização Chen & Cherry 2014), ROUGE (Lin 2004), "
              "METEOR (Banerjee & Lavie 2005, com radicais em português, sem sinônimos), BERTScore (Zhang 2020, "
              "com MiniLM multilíngue: não comparável aos valores publicados com RoBERTa-large). "
              "BLEURT não roda neste PC (TensorFlow + modelo de 2 GB); o juiz por rubrica é o substituto."]
    return "\n".join(lines)
