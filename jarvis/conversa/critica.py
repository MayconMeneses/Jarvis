"""Crítica leve da resposta do modelo local: se saiu curta demais, vaga ou repetida, tenta de novo UMA vez com instrução mais específica.

Só o modelo local passa por aqui (é pequeno e gratuito; refazer não gasta nada). Os cérebros grandes não precisam.
A crítica é determinística (sem outra chamada ao modelo): olha tamanho, frases-muleta e semelhança com a resposta anterior.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable

from jarvis.conversa.reescrita import dobrar

MIN_PALAVRAS_PERGUNTA = 6
MIN_CHARS_RESPOSTA = 60
_MULETAS = re.compile(
    r"^(depende|nao sei|como (uma )?(ia|assistente)|desculpe|infelizmente|nao consigo|e uma otima pergunta|claro[,!])|"
    r"\b(depende de varios fatores|existem varias opcoes|cada caso e um caso)\b")
INSTRUCAO_REFAZER = (
    "Sua resposta anterior ficou {problema}. Responda de novo, de forma específica: comece pela resposta, inclua um exemplo "
    "concreto, um número ou um passo, e feche com um próximo passo. Se realmente não souber, diga o que falta saber. "
    "Não repita a resposta anterior.")


def problema(pergunta: str, resposta: str, anterior: str = "") -> str:
    """'' se a resposta está boa; senão, uma palavra que descreve o defeito (curta, vaga, repetida)."""
    baixa = dobrar(resposta).strip()
    if anterior and difflib.SequenceMatcher(None, baixa, dobrar(anterior).strip()).ratio() > 0.85:
        return "repetida"
    perguntou_muito = len(pergunta.split()) >= MIN_PALAVRAS_PERGUNTA
    if perguntou_muito and len(baixa) < MIN_CHARS_RESPOSTA and "?" not in baixa:
        return "curta demais"
    if perguntou_muito and _MULETAS.search(baixa) and len(baixa) < 220:
        return "vaga"
    return ""


def _melhor(velha: str, nova: str) -> str:
    """Entre duas respostas com defeito, a maior que não é frase-muleta."""
    return nova if len(nova) > len(velha) and not _MULETAS.search(dobrar(nova)) else velha


def melhorar(texto: str, pergunta: str, prompt: list[dict], conversa: Callable[[list[dict]], str], anterior: str = "") -> str:
    """Devolve `texto` se estiver bom; senão tenta uma vez de novo com a instrução e fica com a melhor das duas."""
    defeito = problema(pergunta, texto, anterior)
    if not defeito:
        return texto
    try:
        nova = conversa([*prompt, {"role": "assistant", "content": texto},
                         {"role": "user", "content": INSTRUCAO_REFAZER.format(problema=defeito)}]).strip()
    except Exception:  # a crítica nunca derruba a resposta que já existe
        return texto
    if not nova:
        return texto
    return _melhor(texto, nova) if problema(pergunta, nova, texto) else nova
