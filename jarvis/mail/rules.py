"""Regras fixas (custo zero) e detecção de texto que tenta comandar a IA."""

from __future__ import annotations

import re

from jarvis.mail.base import CATEGORIES, Mail

# Frases típicas de prompt injection em e-mails. Um e-mail com isso nunca vira
# comando: ele é marcado como "Suspeito" para o usuário revisar.
_INJECTION = [
    r"ignor\w*\s+(as\s+|todas\s+as\s+)?(instru|regras|orienta)",
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)",
    r"(system|sistema)\s*prompt",
    r"\b(you are|você é) (now |agora )?(an? |uma? )?(ai|ia|assistant|assistente)\b",
    r"\b(jarvis|claude|assistant|assistente)\s*[,:]\s*(apague|delete|envie|send|execute|run|encaminhe|forward)",
    r"(apague|delete|remova)\s+(todos|todas|all)\b",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION]


def injection_reason(mail: Mail) -> str | None:
    text = f"{mail.assunto}\n{mail.previa}"
    for pattern in _INJECTION_RE:
        match = pattern.search(text)
        if match:
            return f"contém texto que tenta dar ordens à IA: “{match.group(0)[:60]}”"
    return None


def rule_category(mail: Mail, rules: list[dict]) -> str | None:
    """Regras do config.json: {"campo": "remetente"|"assunto", "contem": "...", "categoria": "..."}."""
    for rule in rules:
        field = {"remetente": mail.remetente, "assunto": mail.assunto}.get(rule.get("campo", ""))
        needle = str(rule.get("contem", "")).strip().lower()
        category = rule.get("categoria")
        if field is not None and needle and category in CATEGORIES and needle in field.lower():
            return category
    return None


def annotate(mail: Mail, rules: list[dict]) -> dict:
    """Dados do e-mail para a IA, com a sugestão das regras e o alerta de injeção."""
    data = mail.to_dict()
    reason = injection_reason(mail)
    data["categoria_por_regra"] = "Suspeito" if reason else rule_category(mail, rules)
    if reason:
        data["alerta"] = reason
    return data
