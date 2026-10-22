"""Validação declarativa de uma habilidade (entrada de dados/habilidades.json) e a SKILL-MODELO documentada.

Adicionar uma habilidade nova = acrescentar um objeto em dados/habilidades.json (ou começar copiando dados/modelo.json)
e rodar `python -m pytest tests/test_skill_modelo.py`. Nada de código novo é preciso para uma habilidade que só ensina e
treina; se ela também for MEDIDA em projetos, escreva a checagem em checagens*.py e registre-a em CHECAGENS.
Skills de terceiros NUNCA são baixadas sozinhas: copie, leia, adapte e abra um pull request com o teste.
"""

from __future__ import annotations

import re
from pathlib import Path

MODELO = Path(__file__).parent / "dados" / "modelo.json"
CAMPOS_TEXTO = ("id", "nome", "resumo", "treino")
_ID = re.compile(r"^[a-z][a-z0-9_-]{1,40}$")


def validar(item: dict) -> list[str]:
    """Lista de problemas (vazia = a habilidade está bem formada)."""
    erros = [f"falta '{c}'" for c in CAMPOS_TEXTO if not str(item.get(c, "")).strip()]
    if item.get("id") and not _ID.match(str(item["id"])):
        erros.append("id deve ter só letras minúsculas, números, _ e -")
    if not isinstance(item.get("medida"), bool):
        erros.append("'medida' deve ser true ou false")
    if not (isinstance(item.get("niveis"), list) and len(item["niveis"]) == 3 and all(isinstance(n, str) and n.strip() for n in item["niveis"])):
        erros.append("'niveis' deve ter exatamente 3 textos (iniciante, intermediário, avançado)")
    for campo in ("praticas", "estudar"):
        lista = item.get(campo)
        if not (isinstance(lista, list) and lista and all(isinstance(x, str) and x.strip() for x in lista)):
            erros.append(f"'{campo}' deve ser uma lista de textos não vazia")
    return erros
