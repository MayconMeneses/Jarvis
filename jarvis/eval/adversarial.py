"""Cenários adversariais: texto de terceiros (e-mail, documento, anexo) que tenta dar ordens à IA.

Mede o detector de injeção (precisão, recall, F1). Os casos marcados "critico" são ataques diretos que
nunca podem passar: se um deles escapar, é uma falha de gate, não só uma nota mais baixa na média.
"""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.eval import metrics
from jarvis.mail.base import Mail
from jarvis.mail.rules import injection_reason

DATA = Path(__file__).with_name("data") / "injecao.json"


def detect(text: str) -> bool:
    mail = Mail(id="eval:0", conta="eval", remetente="terceiro@exemplo.com", assunto="", data="", previa=text, nao_lido=True)
    return injection_reason(mail) is not None


def bench_injection(cases: list[dict] | None = None, detector=detect) -> dict:
    cases = cases if cases is not None else json.loads(DATA.read_text(encoding="utf-8"))
    expected = ["injecao" if c["injecao"] else "normal" for c in cases]
    predicted = ["injecao" if detector(c["texto"]) else "normal" for c in cases]
    report = metrics.classification_report(expected, predicted)
    missed = [c["texto"] for c, p in zip(cases, predicted) if c["injecao"] and p == "normal"]
    false_alarms = [c["texto"] for c, p in zip(cases, predicted) if not c["injecao"] and p == "injecao"]
    critical_missed = [c["texto"] for c in cases if c.get("critico") and not detector(c["texto"])]
    return {"relatorio": report["por_classe"].get("injecao", {}), "total": len(cases), "perdidos": missed,
            "alarmes_falsos": false_alarms, "falhas_criticas": critical_missed}


def numeric(result: dict) -> dict:
    scores = result["relatorio"]
    return {"injecao_precisao": scores.get("precisao", 0.0), "injecao_recall": scores.get("recall", 0.0),
            "injecao_f1": scores.get("f1", 0.0),
            "adversarial_falhas": [f"injeção crítica não detectada: {t[:60]}" for t in result["falhas_criticas"]]}


def report_lines(result: dict) -> list[str]:
    s = result["relatorio"]
    lines = ["", "## 5. Cenários adversariais (injeção em texto de terceiros)", "",
             f"Precisão **{s.get('precisao', 0):.2f}** · recall **{s.get('recall', 0):.2f}** · F1 **{s.get('f1', 0):.2f}** "
             f"em {result['total']} textos · falhas críticas: **{len(result['falhas_criticas'])}**"]
    lines += [f"- não detectado: \"{t[:70]}\"" for t in result["perdidos"]]
    lines += [f"- alarme falso: \"{t[:70]}\"" for t in result["alarmes_falsos"]]
    return lines
