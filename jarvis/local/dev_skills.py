"""Habilidades de programação do motor próprio (sem IA): consultar, comparar, recomendar e criar sistemas.

Usa a base curada de jarvis/dev/conhecimento e os modelos prontos de jarvis/dev/modelos.
Criar um sistema só PROPÕE a ação: o usuário aprova o cartão na janela.
"""

from __future__ import annotations

import re

from jarvis.dev import conhecimento, logica, modelos, saber

AREAS = (r"front[\s-]?end", r"back[\s-]?end", r"full[\s-]?stack", r"mobile", r"celular", r"bancos? de dados?", r"linguagens?", r"stacks?")
_AREA = re.compile(r"(?<!\w)(" + "|".join(AREAS) + r")(?!\w)", re.I)
_NAO_E_DE_AREA = re.compile(r"\b(loja|gestao|dashboard|chat|blog|api|site|erp|estoque)\b")
HINT = "\n\nQuer saber mais? Pergunte \"compare <A> e <B>\" ou \"qual stack para <tipo de sistema>\"."


def info(tema: str) -> str | None:
    """Descrição da tecnologia citada, ou None se não estiver na base (aí vale pesquisar na internet)."""
    entry = conhecimento.lookup(tema)
    if entry is None:  # não é uma tecnologia: talvez seja lógica, engenharia, arquitetura, UX ou um padrão ("SOLID", "Observer")
        return saber.explicar(tema, logica.language_in(tema))
    return conhecimento.describe(entry) + "\n\nSe quiser mais detalhes ou novidades, diga \"pesquise sobre " + entry["nome"] + "\"."


def algorithm(text: str) -> str | None:
    """Algoritmo clássico pedido ("busca binária em Java"), ou None se não for um que eu tenha pronto."""
    found = logica.algorithm(text)
    return logica.show(found, logica.language_in(text)) if found else None


def logic(text: str) -> str:
    """Método de resolução de problemas, ou a lista de conceitos/algoritmos que conheço."""
    low = conhecimento.fold(text)
    if re.search(r"\b(algoritmos|conceitos)\b", low):
        return saber.resumo() + "\n\n" + logica.algorithms_overview()
    return logica.method(re.sub(r"^(como|me ajuda a|me ajudar a)\s+(resolver|resolvo|pensar|raciocinar)\s*(sobre|para|o problema de)?\s*", "", text, flags=re.I))


def compare(text: str) -> str:
    found = conhecimento.mentioned(text)
    if len(found) >= 2:
        return conhecimento.compare(found[0], found[1])
    ideas = [item for _, item in saber.citados(text)]  # "pilha e fila", "monólito ou microsserviços", "SOLID e DDD"
    if len(ideas) >= 2:
        return logica.compare_concepts(ideas[0], ideas[1])
    return "Diga os dois itens, por exemplo: \"compare React e Vue\", \"Django ou FastAPI?\" ou \"diferença entre pilha e fila\"."


def recommend(text: str) -> str:
    """Recomenda a stack de um tipo de sistema; se a pergunta for sobre uma área, lista o que conheço dela."""
    areas = [re.sub(r"\s+", " ", m.group(1).lower()) for m in _AREA.finditer(text)]
    if areas and not _NAO_E_DE_AREA.search(conhecimento.fold(text)):
        # "linguagens para back end": a área específica (front/back/full/mobile) vale mais que a palavra genérica
        specific = [a for a in areas if re.match(r"(front|back|full|mobile|celular)", a)]
        return conhecimento.overview((specific or areas)[0])
    return conhecimento.recommend(text)


def _name(text: str) -> str:
    m = re.search(r"(?:chamad[oa]|de nome|com o nome)\s+[\"“']?(?P<n>[^\"”',]+?)[\"”']?(?=\s+(?:com|usando|em|na|no|para|e)\s|$)", text, re.I)
    m = m or re.search(r"\b(?:sistema|projeto|app|aplica[cç][aã]o|site|api)\s+(?:full[\s-]?stack\s+)?(?:de\s+|do\s+|da\s+)?"
                       r"[\"“']?(?!(?:com|usando|em|na|no|para)\s)(?P<n>[A-Za-zÀ-ÿ0-9][\w\- ]*?)[\"”']?(?=\s+(?:com|usando|em|na|no|para)\s|$)", text, re.I)
    name = m["n"].strip() if m else ""
    return "" if name.lower() in {"novo", "nova", "full stack", "fullstack", "full-stack"} else name


def create_system(text: str, cfg, store=None) -> str:
    from jarvis.pc import actions

    folder = re.search(r"\b(?:em|na pasta|dentro de|no diret[oó]rio)\s+(?P<p>[A-Za-z]:\\.+?)\s*$", text, re.I)
    body = text[:folder.start()] if folder else text
    stack = re.search(r"\b(?:com|usando)\s+(?P<s>.+?)\s*$", body, re.I)
    name = _name(body)
    modelo = ""
    if stack:
        try:
            modelo = modelos.normalize(stack["s"])
        except ValueError as exc:
            return f"Não consegui criar: {exc}"
    elif re.search(r"full[\s-]?stack", text, re.I):
        modelo = "fastapi+react"  # a stack que eu recomendo por padrão para sistemas web completos
    if not name:
        return ("Qual o nome do sistema? Exemplo: \"crie um sistema chamado Loja com FastAPI e React em C:\\Users\\voce\\Projetos\".\n\n"
                + conhecimento.types_overview())
    if not folder:
        return (f"Em qual pasta devo criar \"{name}\"? Diga: \"crie um sistema chamado {name}" + (f" com {modelo.replace('+', ' e ')}" if modelo else "")
                + " em C:\\caminho\\da\\pasta\" (a pasta tem que existir; eu crio a subpasta do projeto).")
    try:
        action = actions.propose_new_project(store or actions.ActionStore(), cfg, name, folder["p"], "", "pedido do usuário", modelo)
    except ValueError as exc:
        return f"Não consegui preparar: {exc}"
    return (f"Preparei a criação do projeto **{name}**" + (f" ({modelos.descricao(modelo)})" if modelo else "")
            + ". Confira e aprove o cartão abaixo para eu criar:\n" + action.descricao)
