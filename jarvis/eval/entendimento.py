"""Benchmark do entendimento além das regras: autoconhecimento (treino x retido) e comandos em linguagem natural (retidos).

"Antes" = só as regras (regex) do motor, como era; "depois" = regras + casador. As frases retidas nunca entram nas
frases-exemplo do casador (um teste confere), então a diferença mede generalização de verdade.
"""

from __future__ import annotations

from jarvis.eval.bench import load
from jarvis.local import autoconhecimento, casador, entendimento, frases_comandos


def _acerto_conhecimento(frase: str, esperado: str) -> bool:
    m = entendimento.buscar(frase).melhor
    return bool(m and m.tipo == "conhecimento" and m.id == esperado)


def _acerto_comando(motor, frase: str, esperado: str) -> tuple[bool, bool]:
    """(só regras acertou, regras + casador acertou)"""
    regra = motor.classify(frase)
    antes = bool(regra and regra[0] == esperado)
    if regra:
        return antes, antes
    r = entendimento.buscar(frase)
    return antes, bool(r.melhor and r.melhor.tipo == "comando" and r.melhor.id == esperado and r.nivel != casador.BAIXA)


def medir(motor) -> dict:
    retido = load("autoconhecimento_retido.json")
    treino = [(f, e["id"]) for e in autoconhecimento.todos() for f in e["exemplos"]]
    naturais = load("comandos_naturais_retidos.json")
    pares = [_acerto_comando(motor, f, i) for f, i in naturais]
    # Quantas frases retidas de autoconhecimento as regras sozinhas respondiam certo (nenhuma regra conhece o assunto): 0 por construção.
    return {
        "conhecimento_treino": sum(_acerto_conhecimento(f, i) for f, i in treino) / len(treino), "total_treino": len(treino),
        "conhecimento_retido": sum(_acerto_conhecimento(f, i) for f, i in retido) / len(retido), "total_retido": len(retido),
        "conhecimento_retido_antes": 0.0,
        "comandos_naturais_antes": sum(a for a, _ in pares) / len(pares), "comandos_naturais_depois": sum(d for _, d in pares) / len(pares),
        "total_naturais": len(naturais),
        "intencoes_cobertas": len(frases_comandos.INTENCOES),
    }


def linhas(r: dict) -> list[str]:
    return [
        "**Entendimento além das regras (casador sem IA):**",
        f"- autoconhecimento, frases de treino ({r['total_treino']}): {r['conhecimento_treino']:.1%}",
        f"- autoconhecimento, frases retidas ({r['total_retido']}): {r['conhecimento_retido']:.1%} (antes, só regras: {r['conhecimento_retido_antes']:.1%})",
        f"- comandos em linguagem natural retidos ({r['total_naturais']}): {r['comandos_naturais_antes']:.1%} → {r['comandos_naturais_depois']:.1%}",
    ]
