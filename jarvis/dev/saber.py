"""Busca unificada em tudo que a Jarvis sabe de programação: lógica, tecnologias, engenharia, arquitetura, UX, algoritmos e padrões."""

from __future__ import annotations

from jarvis.dev import engenharia, logica, topicos, ux


def procurar(termo: str) -> tuple[str, dict] | None:
    """(tipo, item) do primeiro lugar que conhece o termo, ou None. Tipos: logica, engenharia, ux, padrao, algoritmo."""
    for tipo, achado in (("engenharia", engenharia.topico(termo)), ("ux", ux.topico(termo)), ("logica", logica.concept(termo))):
        if achado:
            return tipo, achado
    for tipo, achado in (("padrao", engenharia.padrao(termo)), ("algoritmo", logica.algorithm(termo)), ("padrao", engenharia.estrutura(termo))):
        if achado:
            return tipo, achado
    encontrados = citados(termo)
    return encontrados[0] if encontrados else None


def explicar(termo: str, linguagem: str = "python") -> str | None:
    achado = procurar(termo)
    if achado is None:
        return None
    tipo, item = achado
    if tipo == "padrao":
        return engenharia.mostrar_padrao(item, linguagem)
    if tipo == "algoritmo":
        return logica.show(item, linguagem)
    return topicos.descrever(item)


def citados(texto: str) -> list[tuple[str, dict]]:
    """Tópicos citados no texto; os mais específicos (engenharia, UX) vêm antes dos conceitos gerais de lógica."""
    tudo = [("engenharia", i) for i in engenharia.mencionados(texto)] + [("ux", i) for i in ux.mencionados(texto)]         + [("logica", i) for i in logica.mentioned_concepts(texto)]
    return tudo


def resumo() -> str:
    return "\n\n".join([logica.concepts_overview(), engenharia.visao_geral(), engenharia.visao_padroes(), engenharia.visao_estruturas(), ux.visao_geral()])


def total() -> dict[str, int]:
    return {"logica": len(logica.conceitos()), "engenharia": len(engenharia.itens()), "ux": len(ux.itens()),
            "padroes": len(engenharia.padroes()), "estruturas": len(engenharia.estruturas()), "algoritmos": len(logica.algoritmos())}
