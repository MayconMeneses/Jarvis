"""Habilidades de programador no motor próprio (sem IA): avaliar projetos, checklists e plano de evolução.

Tudo somente leitura sobre o projeto avaliado; só a memória da Jarvis guarda o histórico das avaliações.
"""

from __future__ import annotations

import re

from jarvis import memory_db
from jarvis.dev import habilidades, projects
from jarvis.dev.habilidades import evolucao

_ALVO = re.compile(r"(?:projeto|c[oó]digo|reposit[oó]rio|sistema)\s+(?:d[oae]s?\s+)?(?P<n>.+?)\s*$", re.I)
_CAMINHO = re.compile(r"(?P<p>[A-Za-z]:\\.+?)\s*$")
_ELA_MESMA = re.compile(r"\b(voce mesma|si mesma|seu proprio codigo|seu codigo|proprio codigo|o codigo da jarvis|a jarvis)\b")


def _fold(text: str) -> str:
    from jarvis.dev.conhecimento import fold

    return fold(text)


def evaluate(text: str, cfg) -> str:
    """"avalie o projeto Loja" / "revise o código da Jarvis" / "analise C:\\pasta"."""
    mem = memory_db.open_memory(cfg)
    path = _CAMINHO.search(text)
    found = _ALVO.search(text.strip(" ?!."))
    alvo = path["p"].strip('"') if path else (found["n"].strip('"') if found else "")
    if not path and (_ELA_MESMA.search(_fold(text)) or _fold(alvo) in ("jarvis", "super jarvis")):
        from jarvis import selfimprove

        try:  # "avalie o seu código": o repositório da própria Jarvis (só na cópia de desenvolvimento)
            alvo = selfimprove.ensure_registered(cfg)
        except (ValueError, RuntimeError) as exc:
            return str(exc)
    if not alvo:
        return "Qual projeto devo avaliar? Diga: \"avalie o projeto Loja\" ou \"avalie C:\\caminho\\do\\projeto\"."
    try:
        return evolucao.avaliar(cfg, mem, alvo)
    except ValueError as exc:
        return str(exc)


def overview() -> str:
    return habilidades.visao_geral()


def evolve(text: str, cfg) -> str:
    if re.search(r"treino", text, re.I):
        return habilidades.treino_da_semana()
    found = _ALVO.search(text.strip(" ?!."))
    return evolucao.proxima(cfg, memory_db.open_memory(cfg), found["n"].strip('"') if found else "")


def checklist(text: str) -> str:
    topic = re.sub(r"^(checklist|lista de verifica[cç][aã]o)\s+(de|do|da|para)?\s*", "", text.strip(" ?!."), flags=re.I)
    return habilidades.checklist(topic)


def plan(text: str) -> str:
    topic = re.sub(r"^(plano de (estudo|evolu[cç][aã]o)|como (evoluir|melhorar|praticar))\s*(em|de|d[oa]s?|para)?\s*", "", text.strip(" ?!."), flags=re.I)
    return habilidades.plano(topic) if topic and habilidades.habilidade(topic) else overview()


__all__ = ["evaluate", "overview", "evolve", "checklist", "plan", "projects"]
