"""Estudar um assunto sozinha: pesquisa, guarda o resumo (com fontes) como nota e registra o que aprendeu para mostrar ao usuário."""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from jarvis.autonomo.interesses import Assunto
from jarvis.dev.topicos import fold

PREFIXO = "Aprendizado/Autônomo/"
DIAS_ENTRE_ESTUDOS = 14
MAX_NOVIDADES = 30


def _quando(texto: str) -> datetime:
    try:
        return datetime.fromisoformat(texto)
    except (TypeError, ValueError):
        return datetime.min


def ja_estudado(mem, nome: str, agora: datetime, dias: int = DIAS_ENTRE_ESTUDOS) -> bool:
    return agora - _quando(mem.meta("autonomo:estudado:" + fold(nome)) or "") < timedelta(days=dias)


def escolher(mem, assuntos: list[Assunto], agora: datetime, minimo_conhecido: int = 3, minimo_novo: int = 2, quantos: int = 3) -> list[Assunto]:
    """Os assuntos que valem estudar agora: muito mencionados e ainda não estudados nos últimos 14 dias. Os desconhecidos vêm primeiro."""
    elegiveis = [a for a in assuntos if a.mencoes >= (minimo_conhecido if a.conhecido else minimo_novo) and not ja_estudado(mem, a.nome, agora)]
    return sorted(elegiveis, key=lambda a: (a.conhecido, -a.mencoes))[:quantos]


def estudar(mem, assunto: Assunto, pesquisar, formatar, agora: datetime, chave_brave: str | None = None) -> str | None:
    """Pesquisa e guarda. Devolve a referência da nota, ou None se a pesquisa não trouxe nada (aí tenta de novo só depois do prazo)."""
    consulta = assunto.nome if not assunto.conhecido else f"{assunto.nome} boas práticas novidades"
    achado = pesquisar(consulta, 5, brave_key=chave_brave)
    mem.set_meta("autonomo:estudado:" + fold(assunto.nome), agora.isoformat(timespec="seconds"))
    if not achado.get("fontes"):
        return None
    corpo = (f"_Estudado sozinha pela Jarvis em {agora:%d/%m/%Y} porque você perguntou sobre isso {assunto.mencoes} vezes. "
             "Vem da internet e não foi verificado: confira antes de confiar._\n\n" + formatar(consulta, achado))
    ref = mem.put(PREFIXO + assunto.nome, corpo, "aprendizado", resumo=f"Estudado sozinha: {assunto.nome}", title=assunto.nome)
    novidades = json.loads(mem.meta("autonomo:novidades") or "[]")
    novidades.append({"tema": assunto.nome, "ref": ref, "quando": agora.isoformat(timespec="seconds"), "visto": False})
    mem.set_meta("autonomo:novidades", json.dumps(novidades[-MAX_NOVIDADES:], ensure_ascii=False))
    return ref


def resumo(mem, marcar_visto: bool = True) -> str:
    """O que a Jarvis estudou desde a última vez que o usuário viu."""
    novidades = json.loads(mem.meta("autonomo:novidades") or "[]")
    novas = [n for n in novidades if not n["visto"]]
    if not novas:
        recentes = novidades[-3:]
        return ("Ainda não estudei nada novo sozinha desde a última vez." + (" Os últimos assuntos: " + ", ".join(n["tema"] for n in recentes) + "." if recentes else ""))
    linhas = [f"📚 Estudei sozinha {len(novas)} assunto(s) sobre o que mais conversamos:"]
    for n in novas:
        trecho = (mem.get(n["ref"]) or "").split("\n\n", 1)[-1].replace("\n", " ")[:160]
        linhas.append(f"- **{n['tema']}**: {trecho}…  (nota \"{n['ref']}\", não verificado)")
    linhas.append("Você pode ver, editar ou apagar essas notas na janela de memória.")
    if marcar_visto:
        for n in novidades:
            n["visto"] = True
        mem.set_meta("autonomo:novidades", json.dumps(novidades, ensure_ascii=False))
    return "\n".join(linhas)
