"""Régua do cérebro local: tarefas de código pequenas com testes escondidos, para medir cada modelo e cada mudança.

O código do modelo roda num processo separado (`python -I`, com tempo limite): nunca dentro da Jarvis. No app instalado
(sem Python solto) a avaliação avisa que só roda a partir do código-fonte.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from collections.abc import Callable

TAREFAS = [
    ("eh_par", "eh_par(n) devolve True se n é par", [[[4], True], [[7], False], [[0], True]]),
    ("soma_lista", "soma_lista(xs) devolve a soma dos números da lista", [[[[1, 2, 3]], 6], [[[]], 0]]),
    ("maior", "maior(xs) devolve o maior número da lista", [[[[3, 9, 2]], 9], [[[-5, -1]], -1]]),
    ("palindromo", "palindromo(s) devolve True se o texto lido de trás para frente é igual (ignore maiúsculas)", [[["Ana"], True], [["casa"], False]]),
    ("fatorial", "fatorial(n) devolve n! (fatorial(0) é 1)", [[[5], 120], [[0], 1]]),
    ("contar_vogais", "contar_vogais(s) devolve quantas vogais (a, e, i, o, u) o texto tem", [[["banana"], 3], [["xyz"], 0]]),
]
EXECUTOR = (
    "import json,sys\n"
    "d=json.load(sys.stdin)\n"
    "ns={}\n"
    "exec(d['codigo'],ns)\n"
    "f=ns[d['funcao']]\n"
    "print(json.dumps([f(*a)==e for a,e in d['casos']]))\n"
)


def executar(codigo: str, funcao: str, casos: list) -> bool:
    """True se a função passa em todos os casos. Falha, erro ou demora = False."""
    if getattr(sys, "frozen", False):
        raise RuntimeError("a avaliação só roda a partir do código-fonte (precisa do Python)")
    try:
        saida = subprocess.run([sys.executable, "-I", "-c", EXECUTOR], input=json.dumps({"codigo": codigo, "funcao": funcao, "casos": casos}),
                               capture_output=True, text=True, timeout=10)
        return saida.returncode == 0 and all(json.loads(saida.stdout))
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return False


def _codigo(resposta: str) -> str:
    achado = re.search(r"```[\w+\-]*\n(.*?)```", resposta, re.S)
    return (achado.group(1) if achado else resposta).strip()


def avaliar(conversa: Callable[[list[dict]], str], tarefas=TAREFAS, rodar: Callable = executar) -> dict:
    inicio, detalhes = time.time(), {}
    for funcao, enunciado, casos in tarefas:
        pedido = f"Escreva em Python a função {enunciado}. Responda só com o código, em um bloco."
        try:
            detalhes[funcao] = rodar(_codigo(conversa([{"role": "user", "content": pedido}])), funcao, casos)
        except RuntimeError:
            raise
        except Exception:
            detalhes[funcao] = False
    acertos = sum(detalhes.values())
    return {"acertos": acertos, "total": len(tarefas), "nota": round(100 * acertos / len(tarefas)), "detalhes": detalhes,
            "segundos": round(time.time() - inicio)}


def relatorio(modelo: str, r: dict) -> str:
    erros = [f for f, ok in r["detalhes"].items() if not ok]
    return (f"**Avaliação do cérebro local ({modelo}):** {r['acertos']} de {r['total']} tarefas certas (nota {r['nota']}/100) em {r['segundos']} s."
            + (f" Errou: {', '.join(erros)}." if erros else " Acertou tudo."))


def registrar(mem, modelo: str, r: dict) -> str:
    """Guarda a nota no histórico (uma linha JSON por avaliação) e devolve a comparação com a anterior do mesmo modelo."""
    ref = "Avaliações/cérebro-local"
    antigo = mem.get(ref) or "# Avaliações do cérebro local\n"
    anteriores = [json.loads(l) for l in antigo.splitlines() if l.startswith("{")]
    mem.put(ref, antigo.rstrip("\n") + "\n" + json.dumps({"modelo": modelo, "nota": r["nota"], "segundos": r["segundos"]}, ensure_ascii=False) + "\n",
            "avaliacao", title="Avaliações do cérebro local")
    mesmos = [a for a in anteriores if a["modelo"] == modelo]
    if not mesmos:
        return ""
    return f" Antes: {mesmos[-1]['nota']}/100 ({r['nota'] - mesmos[-1]['nota']:+d})."
