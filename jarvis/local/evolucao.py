"""Como a Jarvis está evoluindo no entendimento: relatório semanal, vocabulário e esquecer o que aprendeu. Tudo local."""

from __future__ import annotations

from jarvis.local.aprendizado import Aprendizado


def relatorio(apr: Aprendizado | None = None, dias: int = 7) -> tuple[str, str]:
    """(texto, fala curta). Sem frases suficientes, diz isso em vez de inventar uma taxa."""
    r = (apr or Aprendizado()).resumo(dias)
    total = r["entendidas"] + r["falhas"]
    if total == 0:
        return "Ainda não tenho frases suficientes para medir como estou evoluindo.", "Ainda não tenho frases para medir minha evolução."
    linhas = [f"**Como estou evoluindo (últimos {dias} dias)**",
              f"- Entendi {r['entendidas']} de {total} pedidos ({r['taxa']}%)."]
    if r["frases_falhas"]:
        linhas.append("- Frases que mais falharam: " + "; ".join(f"“{f}” ({n}x)" for f, n in r["frases_falhas"][:3]) + ".")
    if r["total_aprendido"]:
        linhas.append(f"- Aprendi {r['total_aprendido']} jeito(s) seu de falar (apelidos e correções).")
    linhas.append("- Para me ensinar: “quando eu disser X, faça Y”. Para ver tudo: “meu vocabulário”.")
    fala = f"Esta semana entendi {r['taxa']} por cento do que você pediu."
    if r["frases_falhas"]:
        fala += f" A frase que mais falhou foi: {r['frases_falhas'][0][0]}."
    return "\n".join(linhas), fala


def vocabulario(apr: Aprendizado | None = None) -> str:
    r = (apr or Aprendizado()).resumo(7)
    linhas = ["**O que aprendi sobre como você fala**"]
    linhas += ([f"- “{f}” → {rot}" for f, rot in r["apelidos"]] or ["- Nenhum apelido ensinado ainda (diga “quando eu disser X, faça Y”)."])
    if r["correcoes"]:
        linhas.append("Correções que você escolheu:")
        linhas += [f"- “{f}” → {rot}" for f, rot in r["correcoes"]]
    if r["frases_falhas"]:
        linhas.append("Frases que ainda não entendi:")
        linhas += [f"- “{f}” ({n}x)" for f, n in r["frases_falhas"]]
    linhas.append("Tudo fica só neste PC. Para apagar: “apague o que você aprendeu sobre como eu falo”.")
    return "\n".join(linhas)


def esquecer(apr: Aprendizado | None = None) -> str:
    (apr or Aprendizado()).apagar_tudo()
    return "Apaguei tudo o que aprendi sobre como você fala: apelidos, correções e frases que eu não entendi."
