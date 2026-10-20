"""Repetição de tentativas: pass@1 e consistência (pass^k) por cenário.

Modelos de IA não são determinísticos: uma resposta boa uma vez não prova nada. Cada cenário roda k vezes
de forma independente; reportamos a taxa média de acerto (pass@1) e se TODAS as k tentativas passaram (pass^k).
"""

from __future__ import annotations

PASS_SCORE = 6.0  # nota média (0 a 10) a partir da qual uma resposta conta como aprovada


def summarize(attempts: dict[str, list[bool]]) -> dict:
    """attempts: {cenário: [passou na tentativa 1, passou na 2, ...]} → métricas por cenário e gerais."""
    scenarios = {}
    for name, results in attempts.items():
        if not results:
            continue
        scenarios[name] = {"tentativas": len(results), "pass@1": sum(results) / len(results), "pass^k": all(results)}
    total = len(scenarios)
    return {
        "cenarios": scenarios,
        "pass@1": sum(s["pass@1"] for s in scenarios.values()) / total if total else 0.0,
        "pass^k": sum(s["pass^k"] for s in scenarios.values()) / total if total else 0.0,
        "instavel": [n for n, s in scenarios.items() if 0 < s["pass@1"] < 1],
    }


def passed(question: str, answer: str, encoder=None, threshold: float = PASS_SCORE) -> bool:
    from jarvis.eval import quality

    media = quality.evaluate(question, answer, None, encoder).get("media")
    return media is not None and media >= threshold


def run(brain, cases: list[dict], attempts: int, system: str, encoder=None) -> dict:
    """Pergunta tudo `attempts` vezes ao cérebro. Erro ou resposta vazia conta como reprovado."""
    results: dict[str, list[bool]] = {c["pergunta"][:60]: [] for c in cases}
    for _ in range(max(1, attempts)):
        for case in cases:
            try:
                answer = brain.ask([{"role": "user", "content": case["pergunta"]}], system).text
                ok = bool(answer.strip()) and passed(case["pergunta"], answer, encoder)
            except Exception:
                ok = False
            results[case["pergunta"][:60]].append(ok)
    return summarize(results)


def report_lines(name: str, result: dict) -> list[str]:
    lines = [f"- {name}: pass@1 **{result['pass@1']:.0%}** · todas as tentativas passaram (pass^k) em **{result['pass^k']:.0%}** dos cenários"]
    if result["instavel"]:
        lines.append(f"  - instáveis (às vezes passam, às vezes não): {', '.join(result['instavel'])}")
    return lines
