"""Pergunta de acompanhamento: detecta "e o outro?", "me dá um exemplo disso" e acha o assunto em andamento.

Não troca o texto do usuário: devolve o assunto para o contexto dizer ao modelo o que "ele", "isso" e "o outro"
significam, e para a busca de notas/conhecimento usar o assunto junto com a pergunta curta.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_CONTINUA = re.compile(
    r"^(e|mas|entao|ai|agora|tambem|ok|certo|beleza|vale|tipo|isso|essa|esse|aquilo|ele|ela|eles|elas|dele|dela|nisso|nele|nela|"
    r"me da um exemplo|faz isso|resume isso|explica melhor|como assim|por que|porque|qual dos|qual delas|e se|outra|outro)\b")
_PRONOME = re.compile(r"\b(ele|ela|eles|elas|isso|disso|nisso|aquilo|esse|essa|esses|essas|o outro|a outra|dele|dela|deles|delas|desse|dessa)\b")
_ANEXOS = "[arquivos anexados"


def dobrar(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


@dataclass
class Reescrita:
    acompanhamento: bool
    tema: str = ""  # a pergunta anterior do usuário que dá sentido a esta

    def consulta(self, texto: str) -> str:
        """Texto para buscar notas e conhecimento: o assunto em andamento mais a pergunta curta."""
        return f"{self.tema} {texto}".strip() if self.acompanhamento else texto


def _limpo(texto: str) -> str:
    return str(texto).split("\n\n[Arquivos anexados")[0].strip()


def parece_acompanhamento(texto: str) -> bool:
    baixo = dobrar(_limpo(texto)).strip(" ?!.")
    palavras = baixo.split()
    if not palavras:
        return False
    return len(palavras) <= 4 or bool(_CONTINUA.match(baixo)) or (bool(_PRONOME.search(baixo)) and len(palavras) <= 12)


def analisar(texto: str, anteriores: list[dict]) -> Reescrita:
    """`anteriores` = mensagens antes da atual. O tema é a última pergunta do usuário que não era ela mesma um acompanhamento."""
    perguntas = [_limpo(m["content"]) for m in anteriores if m["role"] == "user" and not str(m["content"]).startswith("[")]
    if not perguntas or not parece_acompanhamento(texto):
        return Reescrita(False)
    tema = next((p for p in reversed(perguntas) if not parece_acompanhamento(p)), perguntas[-1])
    return Reescrita(True, tema[:160])
