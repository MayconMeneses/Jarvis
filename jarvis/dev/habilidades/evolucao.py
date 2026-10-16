"""Evolução: guarda cada avaliação na memória da Jarvis e compara com a anterior.

Notas da memória: "Habilidades/Avaliações/<projeto>", uma linha JSON por avaliação (as últimas 50).
Quando o projeto avaliado é o código da própria Jarvis, as melhorias sugeridas entram no caderno de
melhorias (selfimprove): é o ciclo "avaliar → anotar → melhorar-se → avaliar de novo".
"""

from __future__ import annotations

import json
from pathlib import Path

from jarvis.dev import habilidades as hab
from jarvis.dev import projects

MAX_REGISTROS = 50
OTIMO = 90  # a partir daqui o aspecto medido já está ótimo
PREFIXO = "Habilidades/Avaliações/"


def _ref(nome: str) -> str:
    return PREFIXO + (nome.strip() or "projeto")


def historico(mem, nome: str) -> list[dict]:
    texto = mem.get(_ref(nome)) or ""
    registros = []
    for linha in texto.splitlines():
        if linha.startswith("{"):
            try:
                registros.append(json.loads(linha))
            except ValueError:
                continue
    return registros


def registrar(mem, nome: str, analise: dict) -> dict | None:
    """Guarda a avaliação e devolve a anterior (para mostrar a evolução)."""
    antes = historico(mem, nome)
    instantaneo = {"data": analise["data"], "geral": analise["geral"],
                   "aspectos": {i: a["nota"] for i, a in analise["aspectos"].items()}}
    registros = (antes + [instantaneo])[-MAX_REGISTROS:]
    corpo = (f"# Avaliações de habilidades: {nome}\n\nUma linha por avaliação (a Jarvis compara com a anterior).\n\n"
             + "\n".join(json.dumps(r, ensure_ascii=False) for r in registros) + "\n")
    mem.put(_ref(nome), corpo, "avaliacao", title=nome)
    return antes[-1] if antes else None


def tendencia(mem, nome: str) -> str:
    notas = [r["geral"] for r in historico(mem, nome) if r.get("geral") is not None]
    if len(notas) < 2:
        return "Ainda há uma avaliação só: avalie de novo depois de melhorar para ver a evolução."
    return f"Nota geral ao longo do tempo ({len(notas)} avaliações): " + " → ".join(str(n) for n in notas[-8:])


def avaliar(cfg, mem, projeto: str) -> str:
    """Avalia um projeto cadastrado (ou uma pasta), guarda no histórico e devolve o boletim."""
    if Path(projeto.strip().strip('"')).is_absolute():
        nome, pasta = Path(projeto.strip().strip('"')).name, Path(projeto.strip().strip('"'))
    else:
        nome, pasta = projects.resolve(cfg, projeto)
    analise = hab.analisar(pasta)
    anterior = registrar(mem, nome, analise)
    texto = hab.relatorio(analise, anterior) + "\n\n" + tendencia(mem, nome)
    if _eh_a_propria_jarvis(pasta):
        texto += "\n\n" + _anotar_melhorias(mem, analise)
    return texto


def _eh_a_propria_jarvis(pasta: Path) -> bool:
    from jarvis import selfimprove

    raiz = selfimprove.own_repo()
    return raiz is not None and Path(pasta).resolve() == raiz.resolve()


def _anotar_melhorias(mem, analise: dict) -> str:
    from jarvis import selfimprove

    novas = 0
    for id_, aspecto in hab.mais_fracos(analise, 3):
        ideia = f"Melhorar {hab._nome(id_).lower()} ({aspecto['nota']}/100): {aspecto['sugestoes'][0]}"
        novas += bool(selfimprove.add_idea(ideia, "avaliação de habilidades", mem))
    return (f"Anotei {novas} melhoria(s) no caderno de melhorias da própria Jarvis (diga \"Jarvis, melhore-se\" para eu propor a próxima)."
            if novas else "As melhorias sugeridas já estavam no caderno de melhorias da própria Jarvis.")


def proxima(cfg, mem, projeto: str = "") -> str:
    """Qual habilidade praticar agora: a mais fraca da última avaliação do projeto (ou uma sugestão geral)."""
    if projeto.strip():
        nome = projects.resolve(cfg, projeto)[0] if not Path(projeto).is_absolute() else Path(projeto).name
        registros = historico(mem, nome)
        if registros:
            ultima = registros[-1]["aspectos"]
            medidos = sorted((n, i) for i, n in ultima.items() if n is not None)
            if medidos and medidos[0][0] < OTIMO:
                return hab.plano(medidos[0][1]) + f"\n\n(Ponto mais fraco de {nome} na última avaliação: {medidos[0][0]}/100.)"
            if medidos:  # tudo que dá para medir está ótimo: evolua o que não se mede, alternando a cada avaliação
                livres = [h for h in hab.catalogo() if not h["medida"]]
                escolhida = livres[len(registros) % len(livres)]
                return (f"Tudo o que eu consigo medir em {nome} está ótimo (mínimo {medidos[0][0]}/100). Para continuar evoluindo, "
                        "pratique o que não se mede automaticamente:\n\n" + hab.plano(escolhida["id"]))
        return f"Ainda não avaliei {nome}. Peça \"avalie o projeto {nome}\" e eu indico a habilidade mais fraca."
    return hab.plano("logica") + "\n\n(Sem projeto informado, sugeri a base de tudo. Peça \"avalie o projeto X\" para um plano sob medida.)"
