"""Lógica de programação: conceitos, método de resolução e uma biblioteca de algoritmos em várias linguagens.

Base curada e testada, sem IA e sem internet:
- conceitos.json: lógica, variáveis, condicionais, laços, funções, recursão, estruturas de dados,
  complexidade, POO, testes, depuração, banco de dados, APIs, git, segurança, arquitetura...
- algoritmos/*.md: cada algoritmo traz a ideia, o pseudocódigo e o código em Python, JavaScript, Go, Java
  e C#. Python, JavaScript e Go são EXECUTADOS nos testes (casos de entrada e saída); Java e C# seguem
  a mesma lógica mas não são compilados neste projeto: revise ao compilar.

Limite honesto: resolve com certeza os problemas clássicos que estão aqui e ensina o método para o resto.
Problemas novos e sistemas sob medida são feitos pelo Claude Code, que recebe este método como guia.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from jarvis.dev.conhecimento import fold

BASE = Path(__file__).parent
LINGUAGENS = {"python": "Python", "javascript": "JavaScript", "go": "Go", "java": "Java", "csharp": "C#"}
_APELIDOS = {"py": "python", "js": "javascript", "node": "javascript", "nodejs": "javascript", "golang": "go",
             "c#": "csharp", "c sharp": "csharp", "dotnet": "csharp", ".net": "csharp"}
_CAMPOS = ("nome", "aliases", "problema", "complexidade", "funcoes", "casos", "go_teste", "go_saida")


# ── conceitos ────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def conceitos() -> tuple[dict, ...]:
    return tuple(json.loads((BASE / "conceitos.json").read_text(encoding="utf-8")))


def concept(term: str) -> dict | None:
    """O conceito pelo nome (ou apelido). Nome e id têm prioridade sobre apelidos de outros conceitos."""
    cleaned = re.sub(r"^(a|o|as|os|um|uma)\s+", "", fold(term).strip(" ?!."))
    for item in conceitos():
        if cleaned in {fold(item["id"]), fold(item["nome"])}:
            return item
    for item in conceitos():
        if cleaned in {fold(a) for a in item.get("aliases", [])}:
            return item
    return None


def mentioned_concepts(text: str) -> list[dict]:
    """Conceitos citados no texto (palavra inteira), na ordem em que aparecem; o nome mais longo vence."""
    low, hits = fold(text), []
    for item in conceitos():
        best = None
        for name in {fold(item["id"]), fold(item["nome"]), *(fold(a) for a in item.get("aliases", []))}:
            found = re.search(rf"(?<!\w){re.escape(name)}(?!\w)", low)
            if found and (best is None or found.start() < best):
                best = found.start()
        if best is not None:
            hits.append((best, item))
    return [item for _, item in sorted(hits, key=lambda h: h[0])]


def compare_concepts(a: dict, b: dict) -> str:
    return (f"**{a['nome']} × {b['nome']}**\n"
            f"- **{a['nome']}:** {a['resumo']}\n  - Analogia: {a['analogia']}\n"
            f"- **{b['nome']}:** {b['resumo']}\n  - Analogia: {b['analogia']}\n"
            f"- **Erros comuns** — {a['nome']}: {'; '.join(a['erros'])} | {b['nome']}: {'; '.join(b['erros'])}")


def describe_concept(item: dict) -> str:
    out = [f"**{item['nome']}**", item["resumo"], "", "**Como pensar:**"]
    out += [f"- {p}" for p in item["passos"]]
    out += ["", f"**Analogia:** {item['analogia']}", "", "**Exemplo:**", "```", item["exemplo"], "```",
            "**Erros comuns:** " + "; ".join(item["erros"]), "**Para praticar:** " + " · ".join(item["exercicios"])]
    return "\n".join(out)


def concepts_overview() -> str:
    return "**Conceitos de lógica e programação que eu explico:**\n" + "\n".join(
        f"- **{c['nome']}**: {c['resumo'].split('.')[0]}." for c in conceitos())


# ── algoritmos ───────────────────────────────────────────────────────────

def _parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    header, _, body = text.partition("\n\n")
    data: dict = {"id": path.stem}
    for line in header.splitlines():
        key, _, value = line.partition(":")
        if key.strip() in _CAMPOS:
            data[key.strip()] = value.strip()
    data["aliases"] = [a.strip() for a in data.get("aliases", "").split(",") if a.strip()]
    data["funcoes"] = dict(p.strip().split("=") for p in data.get("funcoes", "").split(";") if "=" in p)
    data["casos"] = json.loads(data.get("casos", "[]"))
    sections = re.split(r"^## ", body, flags=re.M)
    for section in sections[1:]:
        title, _, content = section.partition("\n")
        if title.strip() == "Ideia":
            data["ideia"] = [l[2:].strip() for l in content.splitlines() if l.startswith("- ")]
        elif title.strip().startswith("Pseudoc"):
            data["pseudocodigo"] = re.search(r"```\n(.*?)\n```", content, re.S).group(1)
        elif title.strip().startswith("C"):
            data["codigo"] = {m.group(1): m.group(2) for m in re.finditer(r"```(\w+)\n(.*?)\n```", content, re.S)}
    return data


@lru_cache(maxsize=1)
def algoritmos() -> tuple[dict, ...]:
    return tuple(_parse(p) for p in sorted((BASE / "algoritmos").glob("*.md")))


def language_in(text: str, default: str = "python") -> str:
    """A primeira linguagem citada no texto (Python, JS, Go, Java, C#...), ou `default`."""
    low = fold(text)
    first, found = len(low) + 1, default
    for name in [*LINGUAGENS, *_APELIDOS]:
        match = re.search(rf"(?<![\w#.]){re.escape(name)}(?![\w#])", low)
        if match and match.start() < first:
            first, found = match.start(), _APELIDOS.get(name, name)
    return found


def algorithm(term: str) -> dict | None:
    """O algoritmo cujo nome ou apelido aparece no texto (o apelido mais longo vence)."""
    low = fold(term)
    best, best_len = None, 0
    for item in algoritmos():
        for name in [item["nome"], item["id"].replace("_", " "), *item["aliases"]]:
            name = fold(name)
            if len(name) > best_len and re.search(rf"(?<!\w){re.escape(name)}(?!\w)", low):
                best, best_len = item, len(name)
    return best


def show(item: dict, lang: str = "python", with_idea: bool = True) -> str:
    """Explicação + pseudocódigo + código na linguagem pedida (ou aviso, se não houver)."""
    lang = _APELIDOS.get(lang, lang)
    out = [f"**{item['nome']}**: {item['problema']}", f"- **Complexidade:** {item['complexidade']}"]
    if with_idea:
        out += ["", "**Ideia:**"] + [f"- {p}" for p in item["ideia"]]
        out += ["", "**Pseudocódigo:**", "```", item["pseudocodigo"], "```"]
    code = item["codigo"].get(lang)
    if code is None:
        return "\n".join(out) + f"\n\nAinda não tenho esse algoritmo em {lang}. Tenho em: " + ", ".join(LINGUAGENS.values()) + "."
    nota = "" if lang in ("python", "javascript", "go") else "\n_(Este exemplo segue a mesma lógica dos testados, mas não foi compilado aqui: revise ao compilar.)_"
    out += ["", f"**Em {LINGUAGENS[lang]}:**", f"```{lang}", code, "```" + nota]
    return "\n".join(out)


def algorithms_overview() -> str:
    return "**Algoritmos que eu sei escrever (Python, JavaScript, Go, Java e C#):**\n" + "\n".join(
        f"- **{a['nome']}**: {a['problema']}" for a in algoritmos())


# ── método ───────────────────────────────────────────────────────────────

def method(problem: str = "") -> str:
    """O roteiro de resolução; se o problema for um clássico conhecido, já mostra o algoritmo."""
    out = [describe_concept(concept("resolver-problemas"))]
    found = algorithm(problem) if problem.strip() else None
    if found:
        out += ["", f"Isso se parece com um problema clássico que eu conheço, **{found['nome']}**:", "", show(found, language_in(problem))]
    elif problem.strip():
        out += ["", "Não reconheci esse problema entre os clássicos que eu sei resolver pronto. Siga o roteiro acima; "
                    "se quiser, peça para o Claude Code (se estiver ligado) implementar a partir do pseudocódigo que você montar."]
    return "\n".join(out)
