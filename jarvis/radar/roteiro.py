"""Boletim → roteiro feito para o OUVIDO (não para o olho), dentro de um orçamento de palavras.

Estrutura: abertura (3 manchetes) → notícias ("Segundo o veículo...") → conexões (só com IA) → encerramento.
Sem IA a fala é só manchete + frases do lead; o "por que importa" só é falado quando existe de verdade (IA).
O orçamento manda no tamanho: se estourar, os itens de menor nota saem; a velocidade da voz nunca é alterada.
"""

from __future__ import annotations

import re
from datetime import datetime

from jarvis.radar.modelos import Boletim, Item
from jarvis.radar.numeros_pt import _MESES, falar_texto

MAX_PALAVRAS_ITEM = 130
ENCERRAMENTO = "Isso é tudo. Os links estão no boletim escrito de hoje."


def saudacao(hora: int) -> str:
    return "Bom dia" if hora < 12 else "Boa tarde" if hora < 18 else "Boa noite"


def _palavras(texto: str) -> int:
    return len(texto.split())


def _limitar(frases: list[str], maximo: int) -> list[str]:
    saida, total = [], 0
    for frase in frases:
        total += _palavras(frase)
        if saida and total > maximo:
            break
        saida.append(frase)
    return saida


def fala_do_item(item: Item, posicao: int, total: int, nicho: str, com_ia: bool) -> str:
    a = item.artigo
    abertura = "" if posicao == 0 else "Pra fechar. " if posicao == total - 1 else ("Próxima. " if posicao % 2 else f"Ainda em {nicho}. ")
    frases = [f"Segundo o {a.fonte}, {item.manchete.rstrip('.')}."] + [l.rstrip() if l.rstrip().endswith((".", "!", "?", "…")) else l.rstrip() + "." for l in item.linhas[:2]]
    if com_ia and item.por_que:
        frases.append(item.por_que)
    if item.tambem_em:
        frases.append("Também publicado por " + " e ".join(item.tambem_em[:2]) + ".")
    if item.rotulo == "opinião":
        frases.append("É um texto de opinião.")
    elif item.rotulo == "possível paywall":
        frases.append("Resumo parcial: o conteúdo completo é pago.")
    return abertura + " ".join(_limitar(frases, MAX_PALAVRAS_ITEM))


def montar(boletim: Boletim, max_palavras: int = 900, agora: datetime | None = None) -> dict:
    """Devolve {texto, itens (os falados), cortados, palavras}. Itens suspeitos (⚠) nunca são narrados."""
    agora = agora or datetime.now()
    candidatos = sorted((i for i in boletim.itens if not i.suspeito), key=lambda i: i.nota, reverse=True)
    cortados: list[Item] = []

    def compor(itens: list[Item]) -> str:
        manchetes = ". ".join(i.manchete.rstrip(".") for i in itens[:3])
        partes = [f"{'Este é o boletim atrasado de hoje. ' if boletim.atrasado else ''}{saudacao(agora.hour)}. "
                  f"Aqui é o seu radar de {boletim.nicho}, {agora.day} de {_MESES[agora.month - 1]}. Hoje: {manchetes}."]
        partes += [fala_do_item(i, n, len(itens), boletim.nicho, boletim.com_ia) for n, i in enumerate(itens)]
        if boletim.conexoes:
            partes.append("Conexões do dia. " + " ".join(c.rstrip(".") + "." for c in boletim.conexoes[:3]))
        partes.append(ENCERRAMENTO)
        return falar_texto("\n".join(partes))

    texto = compor(candidatos)
    while _palavras(texto) > max_palavras and len(candidatos) > 1:
        cortados.append(candidatos.pop())  # sai o de menor nota
        texto = compor(candidatos)
    return {"texto": texto, "itens": candidatos, "cortados": cortados, "palavras": _palavras(texto)}


def duracao_prevista_s(palavras: int, palavras_por_minuto: int = 180) -> float:
    return 60.0 * palavras / max(60, palavras_por_minuto)


def limpo_para_voz(texto: str) -> bool:
    """Confere o roteiro final: sem URL, Markdown, emoji, colchetes, hashtag nem a palavra "bullet"."""
    return not re.search(r"https?://|www\.|[*_`#>|\[\]]|bullet|[\U0001F000-\U0001FAFF]", texto, re.I)
