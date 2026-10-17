"""Quais assuntos o usuário mais pergunta: lê o diário de pedidos dos últimos dias e conta, por assunto.

Dois tipos de assunto: os que a Jarvis já conhece (base curada: SOLID, FastAPI, Docker...) e os que ela ainda NÃO conhece, tirados de
perguntas como "o que é X", "explique X", "como usar X".
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

from jarvis.dev.topicos import fold

_PERGUNTA = re.compile(
    r"^(?:o que (?:e|sao)|explique|explica|me explica|fale sobre|me fale sobre|conte sobre|descreva|aprenda sobre|pesquise sobre|pesquisa sobre|"
    r"estude sobre|como (?:usar|funciona|instalar|configurar|se usa)|para que serve|quando usar)\s+(?:o |a |os |as |um |uma )?(.+)$")
_COMUNS = {"isso", "aquilo", "voce", "vc", "tudo", "hoje", "agora", "ajuda", "meu pc", "o pc", "a hora", "hora", "data", "clima"}
MAX_PALAVRAS = 4


@dataclass(frozen=True)
class Assunto:
    nome: str           # como mostrar ("Observer", "kubernetes")
    mencoes: int
    conhecido: bool     # já existe na base curada da Jarvis?


def pedidos_recentes(mem, dias: int = 14, hoje: date | None = None) -> list[str]:
    """As frases pedidas pelo usuário nos últimos dias (o diário guarda uma linha "Pedido: ..." por pedido)."""
    hoje = hoje or date.today()
    pedidos: list[str] = []
    for i in range(dias):
        corpo = mem.get(f"Diário/{(hoje - timedelta(days=i)).isoformat()}") or ""
        for linha in corpo.splitlines():
            achado = re.search(r"Pedido: (.+)$", linha)
            if achado:
                pedidos.append(achado.group(1).strip())
    return pedidos


def _desconhecido(frase: str) -> str | None:
    achado = _PERGUNTA.match(fold(frase).strip(" ?!."))
    if not achado:
        return None
    tema = re.sub(r"\s+(em|no|na|com|para|pra|de|do|da)\s+(python|javascript|js|java|go|c#|node|react).*$", "", achado[1]).strip()
    palavras = tema.split()
    if not 1 <= len(palavras) <= MAX_PALAVRAS or tema in _COMUNS or len(tema) < 3:
        return None
    return tema


def contar(pedidos: list[str], saber_explica) -> list[Assunto]:
    """Assuntos por número de menções (cada pedido conta uma vez por assunto).

    `saber_explica(texto)` devolve o item curado citado no texto ou None; é o que separa o conhecido do desconhecido.
    """
    conhecidos: Counter[str] = Counter()
    novos: Counter[str] = Counter()
    for frase in pedidos:
        itens = saber_explica(frase)
        for nome in {i["nome"] for i in itens}:
            conhecidos[nome] += 1
        tema = _desconhecido(frase)
        if tema and not itens:
            novos[tema] += 1
    lista = [Assunto(n, c, True) for n, c in conhecidos.items()] + [Assunto(n, c, False) for n, c in novos.items()]
    return sorted(lista, key=lambda a: (-a.mencoes, a.nome))
