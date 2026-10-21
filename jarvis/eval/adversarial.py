"""Cenários adversariais: texto de terceiros (e-mail, documento, anexo, notícia) que tenta dar ordens à IA.

Dois conjuntos: injecao.json (e-mail/documento, detector do e-mail) e injecao_radar.json (notícias, detector do
Radar, que também enxerga caracteres invisíveis, homóglifos e letras separadas). Os casos marcados "critico"
são ataques diretos que nunca podem passar: se um escapar, é falha de gate, não só nota mais baixa na média.
"""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.eval import metrics
from jarvis.mail.base import Mail
from jarvis.mail.rules import injection_reason

DATA = Path(__file__).with_name("data") / "injecao.json"
DATA_RADAR = Path(__file__).with_name("data") / "injecao_radar.json"


def detect(text: str) -> bool:
    mail = Mail(id="eval:0", conta="eval", remetente="terceiro@exemplo.com", assunto="", data="", previa=text, nao_lido=True)
    return injection_reason(mail) is not None


def detect_radar(text: str) -> bool:
    from jarvis.radar import sanear

    return sanear.suspeito(text) is not None


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


def bench_all() -> dict:
    """O conjunto clássico + o do Radar (em result["radar"])."""
    result = bench_injection()
    result["radar"] = bench_injection(json.loads(DATA_RADAR.read_text(encoding="utf-8")), detect_radar)
    return result


def numeric(result: dict) -> dict:
    scores = result["relatorio"]
    numbers = {"injecao_precisao": scores.get("precisao", 0.0), "injecao_recall": scores.get("recall", 0.0),
               "injecao_f1": scores.get("f1", 0.0),
               "adversarial_falhas": [f"injeção crítica não detectada: {t[:60]}" for t in result["falhas_criticas"]]}
    radar = result.get("radar")
    if radar:
        numbers["radar_injecao_f1"] = radar["relatorio"].get("f1", 0.0)
        numbers["radar_injecao_recall"] = radar["relatorio"].get("recall", 0.0)
        numbers["adversarial_falhas"] += [f"injeção crítica (Radar) não detectada: {t[:60]}" for t in radar["falhas_criticas"]]
    return numbers


def _linhas(titulo: str, r: dict) -> list[str]:
    s = r["relatorio"]
    lines = ["", titulo, "",
             f"Precisão **{s.get('precisao', 0):.2f}** · recall **{s.get('recall', 0):.2f}** · F1 **{s.get('f1', 0):.2f}** "
             f"em {r['total']} textos · falhas críticas: **{len(r['falhas_criticas'])}**"]
    lines += [f"- não detectado: \"{t[:70]}\"" for t in r["perdidos"]]
    lines += [f"- alarme falso: \"{t[:70]}\"" for t in r["alarmes_falsos"]]
    return lines


def report_lines(result: dict) -> list[str]:
    lines = _linhas("## 5. Cenários adversariais (injeção em texto de terceiros)", result)
    if result.get("radar"):
        lines += _linhas("### 5b. Injeção em notícias (Radar: invisíveis, homóglifos, letras separadas)", result["radar"])
    return lines
