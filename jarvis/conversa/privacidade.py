"""O que pode ir para a nuvem: máscara de dados pessoais e áreas sensíveis fora do contexto enviado.

A conversa só vai para provedores que o usuário já ligou (Claude, Gemini, NVIDIA) e nunca no modo "somente independente"
(o roteador esconde esses cérebros). Aqui fica a segunda trava: nota de finanças, saúde e relações não entra no contexto de
nuvem, e CPF, cartão, e-mail, telefone e chaves são mascarados. O modelo local recebe tudo, pois nada sai do PC.
"""

from __future__ import annotations

import re

AREAS_SENSIVEIS = ("financas", "saude", "relacoes")
NUVEM = ("claude", "gemini", "nvidia")
_MASCARAS = (
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[CPF]"),
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[número]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[e-mail]"),
    (re.compile(r"(?:\+?55\s?)?\(?\d{2}\)?\s?9?\d{4}[-\s]?\d{4}\b"), "[telefone]"),
    (re.compile(r"\b(?:sk-|AIza|nvapi-|ghp_|xox[bp]-)[\w-]{10,}"), "[chave]"),
    (re.compile(r"\b[A-Za-z0-9_\-]{40,}\b"), "[chave]"),
)
_SENSIVEL = re.compile(
    r"\b(senha|password|cpf|rg|cartao|cartão|cvv|token|chave de api|api key|pix|saldo|salario|salário|fatura|"
    r"conta bancaria|conta bancária|diagnostico|diagnóstico|remedio|remédio|doenca|doença)\b|R\$\s*\d|\b\d[\d.,]*\s*(reais|mil reais)\b", re.I)


def redigir(texto: str) -> str:
    for padrao, troca in _MASCARAS:
        texto = padrao.sub(troca, texto)
    return texto


def sensivel(texto: str) -> bool:
    """True se o texto parece trazer senha, documento, valor em dinheiro ou dado de saúde (não vira perfil nem lembrança sozinho)."""
    return bool(_SENSIVEL.search(texto)) or redigir(texto) != texto


def area_sensivel(ref: str) -> bool:
    from jarvis import memory_areas

    return memory_areas.area_de(ref) in AREAS_SENSIVEIS
