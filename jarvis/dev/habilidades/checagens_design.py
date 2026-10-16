"""Checagens de arquitetura (ciclos de importação, decisões registradas) e de design de interface (CSS)."""

from __future__ import annotations

import ast
import re

from jarvis.dev.habilidades.base import Resultado, codigo_de, limitar
from jarvis.dev.habilidades.varredura import Projeto, eh_modelo

_DECISOES = ("docs/adr", "adr", "docs/decisoes", "docs/decisoes.md", "docs/decisões.md", "docs/decisões", "architecture.md", "arquitetura.md", "docs/architecture.md", "docs/arquitetura.md")


def _modulo(caminho: str) -> str:
    nome = caminho[:-3].replace("/", ".")
    return nome[: -len(".__init__")] if nome.endswith(".__init__") else nome


def _importados(texto: str, modulos: set[str]) -> set[str]:
    try:
        arvore = ast.parse(texto)
    except (SyntaxError, ValueError):
        return set()
    achados = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes = [no.module] + [f"{no.module}.{a.name}" for a in no.names]
        else:
            continue
        achados |= {n for n in nomes if n in modulos}
    return achados


def ciclos(p: Projeto) -> list[list[str]]:
    """Grupos de módulos Python do projeto que se importam em círculo (componentes fortemente conexos)."""
    fontes = {c: t for c, t in codigo_de(p).items() if c.endswith(".py")}
    modulos = {_modulo(c) for c in fontes}
    grafo = {_modulo(c): _importados(t, modulos) - {_modulo(c)} for c, t in fontes.items()}
    indice, baixo, pilha, na_pilha, grupos = {}, {}, [], set(), []

    def visitar(v: str) -> None:  # Tarjan, iterativo para não estourar a pilha em projetos grandes
        trabalho = [(v, iter(sorted(grafo[v])))]
        indice[v] = baixo[v] = len(indice)
        pilha.append(v)
        na_pilha.add(v)
        while trabalho:
            atual, filhos = trabalho[-1]
            for w in filhos:
                if w not in indice:
                    indice[w] = baixo[w] = len(indice)
                    pilha.append(w)
                    na_pilha.add(w)
                    trabalho.append((w, iter(sorted(grafo[w]))))
                    break
                if w in na_pilha:
                    baixo[atual] = min(baixo[atual], indice[w])
            else:
                trabalho.pop()
                if trabalho:
                    pai = trabalho[-1][0]
                    baixo[pai] = min(baixo[pai], baixo[atual])
                if baixo[atual] == indice[atual]:
                    grupo = []
                    while True:
                        w = pilha.pop()
                        na_pilha.discard(w)
                        grupo.append(w)
                        if w == atual:
                            break
                    if len(grupo) > 1:
                        grupos.append(sorted(grupo))

    for v in sorted(grafo):
        if v not in indice:
            visitar(v)
    return grupos


def arquitetura(p: Projeto) -> Resultado:
    codigo = codigo_de(p)
    if len(codigo) < 2:
        return Resultado(None, ["Projeto com menos de dois arquivos de código: arquitetura não se aplica."])
    nota, achados, ajuda = 40, [], []
    pastas = {c.rsplit("/", 1)[0] for c in codigo if "/" in c}
    if pastas:
        nota += 15
        achados.append(f"Código dividido em {len(pastas)} pasta(s)/módulo(s).")
    else:
        ajuda.append("Separe o código em pastas por responsabilidade (interface, regra de negócio, dados).")
    grupos = ciclos(p)
    if grupos:
        nota -= min(30, 10 * len(grupos))
        achados.append(f"{len(grupos)} ciclo(s) de importação: " + "; ".join(" ↔ ".join(g[:4]) for g in grupos[:3]) + ".")
        ajuda.append("Quebre o ciclo movendo o código compartilhado para um terceiro módulo ou invertendo a dependência (interface).")
    elif any(c.endswith(".py") for c in codigo):
        nota += 30
        achados.append("Sem ciclos de importação entre os módulos Python.")
    else:
        nota += 15
    if any(p.existe(d) for d in _DECISOES) or any(a.lower().startswith(("docs/adr", "adr/")) for a in p.arquivos):
        nota += 15
        achados.append("Decisões de arquitetura registradas.")
    else:
        ajuda.append("Registre as decisões importantes (ADR) em docs/adr: o que foi escolhido, por quê e o que muda.")
    return Resultado(limitar(nota), achados, ajuda)


def design_de_interface(p: Projeto) -> Resultado:
    estilos = {c: t for c, t in p.textos.items() if c.endswith(".css") and not eh_modelo(c)}
    for caminho, texto in p.textos.items():
        if caminho.endswith(".html") and not eh_modelo(caminho):
            estilos[caminho] = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", texto, re.S | re.I))
    css = "\n".join(estilos.values())
    if not css.strip():
        return Resultado(None, ["Sem CSS: não se aplica."])
    nota, achados, ajuda = 0, [], []

    def conferir(ok: bool, pontos: int, bom: str, falta: str) -> None:
        nonlocal nota
        if ok:
            nota += pontos
            achados.append(bom)
        else:
            ajuda.append(falta)

    conferir(bool(re.search(r"--[\w-]+\s*:", css)) and "var(" in css, 20, "Usa variáveis CSS (tokens).",
             "Defina cores, tamanhos e espaçamentos como variáveis (--cor-principal) em :root.")
    conferir(bool(re.search(r"@media[^{]*(min|max)-width", css)), 20, "Tem media queries de largura.",
             "Adicione media queries para adaptar o layout a telas pequenas (mobile-first).")
    foco = ":focus-visible" in css or ":focus" in css
    conferir(foco and not re.search(r"outline\s*:\s*(none|0)\b", css) or ":focus-visible" in css, 15, "Define estilo de foco.",
             "Garanta foco visível para teclado (:focus-visible) e nunca remova o outline sem substituto.")
    conferir("prefers-color-scheme" in css, 15, "Respeita o tema claro/escuro do sistema.", "Considere prefers-color-scheme para o tema escuro.")
    animado = bool(re.search(r"\b(animation|transition)\s*:", css))
    conferir(not animado or "prefers-reduced-motion" in css, 15, "Animações respeitam o movimento reduzido." if animado else "Sem animações a controlar.",
             "Desligue animações em prefers-reduced-motion: reduce.")
    unidades = len(re.findall(r"\d(rem|em|vh|vw|%)\b|clamp\(|minmax\(", css))
    conferir(unidades > 0, 15, "Usa unidades relativas/fluidas (rem, %, clamp).", "Prefira rem, % e clamp() a pixels fixos para o texto e o layout.")
    return Resultado(limitar(nota), achados, ajuda)
