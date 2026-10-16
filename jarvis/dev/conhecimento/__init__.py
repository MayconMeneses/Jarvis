"""Conhecimento da Jarvis sobre linguagens, frameworks, bancos e stacks (front end, back end e full stack).

É uma base curada, escrita à mão em dados/*.json, que funciona sem IA e sem internet: descreve
cada tecnologia, compara duas, e recomenda uma stack para um tipo de sistema. A criação de
projetos iniciais a partir dessa recomendação está em jarvis/dev/modelos/.

Limite honesto: isto NÃO é conhecimento ilimitado de programação. Sistemas sob medida, além
dos modelos prontos, continuam sendo feitos pelo Claude Code (que recebe esta base como guia).
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

DADOS = Path(__file__).parent / "dados"
AREAS = {"front": "front-end", "back": "back-end", "full": "full stack", "mobile": "mobile"}
CATEGORIAS = {"linguagem": "Linguagens", "front": "Front-end", "back": "Back-end", "banco": "Bancos de dados",
              "stack": "Stacks full stack", "full": "Full stack", "mobile": "Mobile"}


def fold(text: str) -> str:
    """Minúsculas e sem acentos (mantém # e + de "c#" e "c++")."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


@lru_cache(maxsize=1)
def entries() -> tuple[dict, ...]:
    found = []
    for name in ("linguagens", "front", "back", "bancos_stacks"):
        found += json.loads((DADOS / f"{name}.json").read_text(encoding="utf-8"))
    return tuple(found)


@lru_cache(maxsize=1)
def system_types() -> tuple[dict, ...]:
    return tuple(json.loads((DADOS / "tipos_de_sistema.json").read_text(encoding="utf-8")))


def _names(entry: dict) -> set[str]:
    return {fold(entry["id"]), fold(entry["nome"])} | {fold(a) for a in entry.get("aliases", [])}


def lookup(term: str) -> dict | None:
    """A tecnologia com esse nome (ou apelido); aceita "a linguagem Python", "o framework React"."""
    cleaned = re.sub(r"^(a|o|as|os|uma|um)\s+(linguagem|framework|biblioteca|banco|stack|tecnologia)\s+(de\s+)?", "", fold(term).strip(" ?!"))
    cleaned = re.sub(r"^(a|o)\s+", "", cleaned)
    for candidate in (cleaned, cleaned.rstrip(".")):  # ".net" começa com ponto; "react." termina
        for entry in entries():
            if candidate in _names(entry):
                return entry
    return None


def mentioned(text: str) -> list[dict]:
    """Tecnologias citadas no texto (palavra inteira), na ordem em que aparecem."""
    low = fold(text)
    hits = []
    for entry in entries():
        for name in _names(entry):
            found = re.search(rf"(?<![\w#+.]){re.escape(name)}(?![\w#+])", low)
            if found:
                hits.append((found.start(), entry))
                break
    return [entry for _, entry in sorted(hits, key=lambda h: h[0])]


def by_area(area: str) -> list[dict]:
    """Tecnologias de uma área ("front", "back", "full", "mobile") ou categoria ("banco", "linguagem", "stack")."""
    area = fold(area)
    aliases = {"front end": "front", "frontend": "front", "front-end": "front", "back end": "back", "backend": "back",
               "back-end": "back", "full stack": "full", "fullstack": "full", "full-stack": "full",
               "banco de dados": "banco", "bancos": "banco", "bancos de dados": "banco", "linguagens": "linguagem",
               "stacks": "stack", "celular": "mobile"}
    area = aliases.get(area, area)
    if area in ("banco", "linguagem", "stack"):
        return [e for e in entries() if e["categoria"] == area]
    return [e for e in entries() if area in e.get("areas", []) and e["categoria"] not in ("banco",)]


def _bullets(items: list[str]) -> str:
    return "\n".join(f"  - {item}" for item in items)


def describe(entry: dict) -> str:
    return (f"**{entry['nome']}** ({CATEGORIAS.get(entry['categoria'], entry['categoria'])}): {entry['resumo']}\n"
            f"- **Usos:** {'; '.join(entry['usos'])}\n"
            f"- **Pontos fortes:** {'; '.join(entry['fortes'])}\n"
            f"- **Pontos fracos:** {'; '.join(entry['fracos'])}\n"
            f"- **Quando escolher:** {'; '.join(entry['quando'])}\n"
            f"- **Curva de aprendizado:** {entry['curva']}\n"
            f"- **Como começar:** {' → '.join(f'`{c}`' for c in entry['comeco'])}")


def overview(area: str) -> str:
    items = by_area(area)
    if not items:
        return "Não conheço essa área. Pergunte por front end, back end, full stack, mobile, bancos de dados ou linguagens."
    title = AREAS.get(fold(area), CATEGORIAS.get(fold(area), area))
    lines = [f"- **{e['nome']}**: {e['resumo']}" for e in items]
    return f"**{title.capitalize()}: o que eu conheço**\n" + "\n".join(lines) + \
        "\n\nPergunte \"o que é <nome>\", \"compare <A> e <B>\" ou \"qual stack para <tipo de sistema>\"."


def compare(a: dict, b: dict) -> str:
    def row(label: str, key: str) -> str:
        return f"- **{label}** — {a['nome']}: {'; '.join(a[key])} | {b['nome']}: {'; '.join(b[key])}"

    return (f"**{a['nome']} × {b['nome']}**\n"
            f"- **O que é** — {a['nome']}: {a['resumo']} | {b['nome']}: {b['resumo']}\n"
            f"{row('Pontos fortes', 'fortes')}\n{row('Pontos fracos', 'fracos')}\n{row('Quando escolher', 'quando')}\n"
            f"- **Curva** — {a['nome']}: {a['curva']} | {b['nome']}: {b['curva']}\n"
            "Se a pergunta for de qual é melhor: depende do projeto; diga o tipo de sistema e eu recomendo uma stack.")


def _score(kind: dict, text: str) -> int:
    score = 0
    for word in kind["palavras"]:
        if re.search(rf"(?<!\w){re.escape(fold(word))}(?!\w)", text):
            score += 1 + len(word.split())  # frases mais específicas pesam mais
    return score


def match_type(description: str) -> dict | None:
    text = fold(description)
    ranked = sorted(((_score(kind, text), kind) for kind in system_types()), key=lambda r: -r[0])
    return ranked[0][1] if ranked and ranked[0][0] > 0 else None


def types_overview() -> str:
    return "**Tipos de sistema que sei recomendar:** " + ", ".join(kind["nome"] for kind in system_types()) + "."


def recommend(description: str) -> str:
    kind = match_type(description)
    if kind is None:
        return ("Não entendi que tipo de sistema é. Diga, por exemplo, \"loja virtual\", \"sistema de gestão\", "
                "\"API\", \"dashboard\", \"aplicativo de celular\", \"chat em tempo real\" ou \"site institucional\".\n"
                + types_overview())
    names = lambda ids: ", ".join(lookup(i)["nome"] for i in ids if lookup(i))  # noqa: E731
    lines = [f"**Para {kind['nome'].lower()}, eu recomendo:**"]
    for label, key in (("Front-end", "front"), ("Back-end", "back"), ("Banco de dados", "banco")):
        if kind[key]:
            lines.append(f"- **{label}:** {names(kind[key])}")
    lines.append(f"- **Por quê:** {kind['motivo']}")
    if kind["alternativas"]:
        lines.append("- **Alternativas:** " + "; ".join(kind["alternativas"]))
    if kind["modelo"]:
        lines.append(f"\nPosso criar um projeto inicial pronto para rodar (modelo `{kind['modelo']}`): diga "
                     "\"crie um sistema chamado <nome> com FastAPI e React em <pasta>\" e eu proponho a criação para você aprovar.")
    return "\n".join(lines)
