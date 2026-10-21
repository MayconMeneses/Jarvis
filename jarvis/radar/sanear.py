"""Saneamento de texto de terceiros (feed, página, anexo) e alerta de injeção de prompt.

A segurança do Radar NÃO depende deste detector: o texto de artigo nunca chega a uma IA com ferramentas e
nada do que ele diz vira ação. O detector é uma camada de ALERTA (o item é marcado ⚠ e não vai à IA).
"""

from __future__ import annotations

import re
import unicodedata

from jarvis.mail.rules import texto_suspeito
from jarvis.radar.feed_parse import limpar

# Letras de outros alfabetos que parecem latinas (ataque de homóglifos): cirílico e grego mais usados.
_PARES = {"а": "a", "в": "b", "е": "e", "ё": "e", "з": "3", "и": "u", "і": "i", "ј": "j", "к": "k", "м": "m", "н": "h", "о": "o", "п": "n", "р": "p", "с": "c", "т": "t", "у": "y", "х": "x", "ѕ": "s", "ԁ": "d", "ԛ": "q", "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x"}
_HOMOGLIFOS = str.maketrans(_PARES)
_SEPARADAS = re.compile(r"\b(?:[^\W\d_][\-._*]){1,}[^\W\d_]\b")  # letras soltas unidas por - . _ * (uma palavra)
_EXTRAS = [re.compile(p) for p in (
    r"(desconsider|esquec|ignor)\w*\s+(tudo|todas?|isso|o que|as|os)\b.{0,40}\b(antes|anterior|acima|dito|regras|instrucoes)",
    r"(ignore|disregard|forget)\s+(all|everything|the)\b.{0,30}\b(above|previous|prior|instructions|rules)",
    r"(ignora|olvida)\s+las?\s+instrucciones",
    r"\b(novo|nova)\s+(objetivo|missao|tarefa|instrucao)\s*:",
    r"\b(copi|envi|mand|encaminh|revel|vaz)\w*\s+(as\s+|os\s+|a\s+|o\s+|seu\s+|sua\s+|todos\s+os\s+)?(senhas?|chaves?|tokens?|credenciais|prompt|memoria|dados)\b",
    r"(you are now|developer mode|jailbreak|modo desenvolvedor|modo deus)",
    r"(responda|reply|answer)\s+(apenas|only)\s+com",
    r"\b(jarvis|assistente|assistant)\s*[,:]\s*(adicione|acesse|abra|visite|instale|baixe|add|open|visit|install|download)\b",
    r"(new system prompt|system prompt|prompt de sistema|prompt do sistema)",
    r"(chame|call|invoke|execute|use)\s+(a\s+)?(ferramenta|tool|function|funcao)\b",
    r"</?\s*(system|assistant|user)\s*>",
    r"(que|that)\s+(o\s+)?(assistente|assistant|ia|ai)\s+(deve|devera|should|must)\s+(ignorar|ignore|enviar|send|apagar|delete)",
)]


def normalizar(texto: str) -> str:
    """NFKC (largura total vira normal), sem caracteres invisíveis/de controle, homóglifos trocados por letras latinas."""
    texto = unicodedata.normalize("NFKC", texto or "")
    texto = "".join(c for c in texto if unicodedata.category(c) not in ("Cf", "Co", "Cn") and (unicodedata.category(c) != "Cc" or c in "\n\t"))
    return texto.translate(_HOMOGLIFOS)


def desofuscar(texto: str) -> str:
    """"i-g-n-o-r-e" e "i.g.n.o.r.e" voltam a ser "ignore"."""
    return _SEPARADAS.sub(lambda m: re.sub(r"[\-._*]", "", m.group(0)), texto)


def limpar_terceiros(texto: str, limite: int = 4000) -> str:
    """HTML/script/comentário fora, invisíveis fora, tamanho limitado. É o que qualquer parte do Radar pode usar."""
    texto = re.sub(r"<!--.*?-->", " ", texto or "", flags=re.S)
    return limpar(normalizar(texto), limite)


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def suspeito(texto: str) -> str | None:
    """Motivo, se o texto tenta dar ordens à IA (ou ao Radar); None se parece uma notícia normal."""
    limpo = normalizar(texto)
    for variante in (limpo, desofuscar(limpo)):
        trecho = texto_suspeito(variante)
        if trecho:
            return f"contém texto que tenta dar ordens à IA: “{trecho}”"
        dobrado = _sem_acento(variante)
        for padrao in _EXTRAS:
            achou = padrao.search(dobrado)
            if achou:
                return f"contém texto que tenta dar ordens à IA: “{achou.group(0)[:60]}”"
    return None
