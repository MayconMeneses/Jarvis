"""As 8 áreas do Second Brain: a área de uma nota sai do prefixo do `ref` (nada muda no banco).

Usado pela memória viva (pasta onde a lembrança aprovada é gravada) e pelo mapa/grafo da janela.
"""

from __future__ import annotations

import re
import unicodedata

# id, nome, cor fixa do grafo, pastas (prefixos de ref) que pertencem à área.
AREAS: tuple[dict, ...] = (
    {"id": "metas", "nome": "Metas", "cor": "#fbbf24", "pastas": ("Metas/",)},
    {"id": "trabalho", "nome": "Trabalho", "cor": "#ff5547", "pastas": ("Trabalho/", "Carreira/", "Perfil Profissional")},
    {"id": "projetos", "nome": "Projetos", "cor": "#8b7cff", "pastas": ("Projetos/",)},
    {"id": "financas", "nome": "Finanças", "cor": "#f7931a", "pastas": ("Finanças/",)},
    {"id": "aprendizado", "nome": "Aprendizado", "cor": "#2dd4ff", "pastas": ("Aprendizado/", "Aprendido/", "Pesquisas/")},
    {"id": "saude", "nome": "Saúde", "cor": "#10b981", "pastas": ("Saúde/",)},
    {"id": "relacoes", "nome": "Relações", "cor": "#ec4899", "pastas": ("Relações/",)},
    {"id": "meta", "nome": "Geral", "cor": "#8a90a6", "pastas": ()},  # tudo que não é das outras (Memória/, Diário/...)
)
IDS = tuple(a["id"] for a in AREAS)
_POR_ID = {a["id"]: a for a in AREAS}
MAX_NOS = 150
_LIGACAO = re.compile(r"\[\[([^\[\]|]{1,120})\]\]")


def _fold(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def normalizar(area: str) -> str | None:
    """'Finanças', ' SAUDE ' -> id da área; fora da lista fechada -> None."""
    achada = _fold(str(area)).strip()
    return achada if achada in _POR_ID else None


def area_de(ref: str) -> str:
    for area in AREAS:
        if any(ref.startswith(p) for p in area["pastas"]):
            return area["id"]
    return "meta"


def pasta_de(area: str) -> str:
    """Pasta onde as lembranças da área são gravadas; a área 'meta' usa a pasta de sempre, Memória/."""
    pastas = _POR_ID[area]["pastas"]
    return pastas[0] if pastas and pastas[0].endswith("/") else "Memória/"


def ligacoes(corpo: str) -> set[str]:
    """Títulos citados como [[Título]] no texto da nota."""
    return {m.strip() for m in _LIGACAO.findall(corpo or "")}


def grafo(notas: list[dict]) -> dict:
    """{areas, nos, arestas} para o desenho. `notas`: dicts com ref, corpo e (opcional) atualizado.

    Sem Diário/ (ruído). Arestas: [[ligações]] entre notas e notas da mesma pasta (vizinhas na lista, para não
    explodir). Os nós vêm mais recentes primeiro, no máximo MAX_NOS; o `grau` é o número de conexões.
    """
    uteis = [n for n in notas if not n["ref"].startswith("Diário/")][:MAX_NOS]
    por_titulo = {n["ref"].rsplit("/", 1)[-1].lower(): i for i, n in enumerate(uteis)}
    arestas: set[tuple[int, int]] = set()
    for i, nota in enumerate(uteis):
        for titulo in ligacoes(nota.get("corpo", "")):
            j = por_titulo.get(titulo.lower())
            if j is not None and j != i:
                arestas.add((min(i, j), max(i, j)))
    ultimo_da_pasta: dict[str, int] = {}
    for i, nota in enumerate(uteis):
        pasta = nota["ref"].rsplit("/", 1)[0] if "/" in nota["ref"] else ""
        if pasta in ultimo_da_pasta:
            arestas.add((ultimo_da_pasta[pasta], i))
        ultimo_da_pasta[pasta] = i
    grau = [0] * len(uteis)
    for a, b in arestas:
        grau[a] += 1
        grau[b] += 1
    nos = [{"ref": n["ref"], "area": area_de(n["ref"]), "grau": grau[i]} for i, n in enumerate(uteis)]
    return {"areas": [{"id": a["id"], "nome": a["nome"], "cor": a["cor"]} for a in AREAS],
            "nos": nos, "arestas": sorted([a, b] for a, b in arestas)}
