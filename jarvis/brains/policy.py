"""Qual cérebro tenta primeiro, de acordo com a necessidade.

- Pedido explícito ("Gemini, ...", "pergunte ao Gemini ...") vai para o Gemini.
- No modo "simples", conversa curta sem ferramentas vai para o Gemini, economizando o
  limite do Claude. Tudo que precisa de ferramentas (PC, e-mail, arquivos, internet,
  código, memória) fica com o Claude, o único que as usa.
- No modo "reserva" (padrão), o Gemini só entra se o Claude falhar.
"""

from __future__ import annotations

import re
import unicodedata

MODES = ("reserva", "simples")
_EXPLICIT = re.compile(
    r"^\s*(ei,?\s*|ok,?\s*)?gemini\s*[,:]|\b(pergunt\w*|use|usa|usar|com|pede|peca)\s+(ao|a|o|pro|pra|para o)?\s*gemini\b"
)
# Pedidos que precisam das ferramentas do Claude.
_NEEDS_TOOLS = re.compile(
    r"\b(pc|computador|ram|cpu|disco|memoria|processo|e-?mails?|gmail|outlook|abr\w+|tela|"
    r"vagas?|projetos?|codigo|pesquis\w*|internet|sites?|clima|tempo|noticias?|arquivos?|"
    r"documentos?|planilha|word|excel|pdf|powerpoint|lembr\w*|anex\w*|obsidian|notas?|"
    r"limp\w*|inicializa\w*|instal\w*|cidade|perfil|hoje|agora|atual\w*)\b"
)


def _fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def preferred(text: str, mode: str) -> str | None:
    """Nome do cérebro a tentar primeiro, ou None para a ordem normal."""
    low = _fold(text)
    if _EXPLICIT.search(low):
        return "gemini"
    if mode == "simples" and len(low) <= 160 and "[arquivos anexados" not in low and not _NEEDS_TOOLS.search(low):
        return "gemini"
    return None
