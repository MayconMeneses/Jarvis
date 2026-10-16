"""Habilidades de programador: o que a Jarvis precisa dominar, como mede cada uma e como evolui.

- dados/habilidades.json: 18 habilidades (lógica, linguagens, estruturas, testes, depuração, código limpo,
  segurança, bancos, APIs, arquitetura, versionamento, automação, desempenho, observabilidade,
  acessibilidade, documentação, organização, aprendizado contínuo), cada uma com três níveis, práticas,
  o que estudar e um treino.
- analisar(): avalia um projeto, só leitura, nos aspectos que dão para medir sem IA (9 deles) e dá uma nota
  de 0 a 100 por aspecto, o que achou e o que melhorar.
- A evolução fica na memória (historico.py): cada avaliação é guardada e comparada com a anterior, e a
  próxima habilidade a praticar é a mais fraca. Ao avaliar o código da própria Jarvis, as melhorias entram
  no caderno de melhorias (selfimprove).

Limite honesto: são heurísticas. Ajudam a enxergar lacunas e acompanhar o progresso; não substituem a
revisão feita por uma pessoa nem fazem de ninguém "o melhor programador" sozinhas.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

from jarvis.dev.conhecimento import fold
from jarvis.dev.habilidades.checagens import CHECAGENS
from jarvis.dev.habilidades.varredura import escanear

DADOS = Path(__file__).parent / "dados" / "habilidades.json"
NIVEIS = ("iniciante", "intermediário", "avançado")


@lru_cache(maxsize=1)
def catalogo() -> tuple[dict, ...]:
    return tuple(json.loads(DADOS.read_text(encoding="utf-8")))


def habilidade(termo: str) -> dict | None:
    """A habilidade pelo id ou nome (sem acento), aceitando partes do nome ("testes", "segurança")."""
    low = fold(termo).strip(" ?!.")
    for item in catalogo():
        if low in (fold(item["id"]), fold(item["nome"])):
            return item
    for item in catalogo():
        if low and (low in fold(item["nome"]) or fold(item["id"]) in low.split()):
            return item
    return None


def nivel(nota: int | None) -> str:
    if nota is None:
        return "não medido"
    return NIVEIS[2] if nota >= 80 else NIVEIS[1] if nota >= 55 else NIVEIS[0]


def analisar(pasta: str | Path) -> dict:
    """Avalia o projeto (somente leitura). Devolve {pasta, arquivos, aspectos:{id:{nota,nivel,achados,sugestoes}}, geral}."""
    projeto = escanear(pasta)
    aspectos = {}
    for id_, checagem in CHECAGENS.items():
        resultado = checagem(projeto)
        aspectos[id_] = {"nota": resultado.nota, "nivel": nivel(resultado.nota), "achados": resultado.achados,
                         "sugestoes": resultado.sugestoes}
    notas = [a["nota"] for a in aspectos.values() if a["nota"] is not None]
    return {"pasta": str(projeto.raiz), "arquivos": len(projeto.arquivos), "truncado": projeto.truncado,
            "data": datetime.now().isoformat(timespec="seconds"), "aspectos": aspectos,
            "geral": round(sum(notas) / len(notas)) if notas else None}


def mais_fracos(analise: dict, quantos: int = 3) -> list[tuple[str, dict]]:
    medidos = [(i, a) for i, a in analise["aspectos"].items() if a["nota"] is not None and a["sugestoes"]]
    return sorted(medidos, key=lambda par: par[1]["nota"])[:quantos]


def _nome(id_: str) -> str:
    item = habilidade(id_)
    return item["nome"] if item else id_


def relatorio(analise: dict, anterior: dict | None = None) -> str:
    """Boletim em Markdown, com a evolução em relação à avaliação anterior (se houver)."""
    out = [f"**Avaliação de {Path(analise['pasta']).name}** ({analise['arquivos']} arquivos) — nota geral: "
           f"**{analise['geral']}/100** ({nivel(analise['geral'])})"]
    if anterior and anterior.get("geral") is not None and analise["geral"] is not None:
        delta = analise["geral"] - anterior["geral"]
        out.append(f"Evolução desde {anterior['data'][:10]}: {delta:+d} ponto(s) (era {anterior['geral']}).")
    for id_, a in analise["aspectos"].items():
        if a["nota"] is None:
            out.append(f"- **{_nome(id_)}**: não se aplica ({a['achados'][0]})")
            continue
        seta = ""
        if anterior and anterior.get("aspectos", {}).get(id_) is not None:
            d = a["nota"] - anterior["aspectos"][id_]
            seta = f" ({d:+d})" if d else ""
        out.append(f"- **{_nome(id_)}**: {a['nota']}/100, {a['nivel']}{seta}")
        out += [f"  - {x}" for x in a["achados"]]
    fracos = mais_fracos(analise)
    if fracos:
        out += ["", "**O que melhorar primeiro:**"]
        for id_, a in fracos:
            out += [f"- {_nome(id_)} ({a['nota']}/100): {a['sugestoes'][0]}"]
    if analise["truncado"]:
        out.append("\n_(Projeto muito grande: analisei só os primeiros arquivos.)_")
    out.append("\n_São sinais automáticos, não um veredito: confirme numa revisão de código de verdade._")
    return "\n".join(out)


def checklist(termo: str) -> str:
    item = habilidade(termo)
    if item is None:
        return "Não conheço esse aspecto. " + visao_geral()
    out = [f"**Checklist: {item['nome']}**", item["resumo"], "", "**Práticas para conferir:**"]
    out += [f"- [ ] {p}" for p in item["praticas"]]
    out += ["", "**Níveis:**"] + [f"- {n}: {t}" for n, t in zip(NIVEIS, item["niveis"])]
    return "\n".join(out)


def plano(termo_ou_analise) -> str:
    """Como evoluir uma habilidade: o que fazer, o que estudar e um treino."""
    from jarvis.dev import conhecimento, logica

    item = habilidade(termo_ou_analise) if isinstance(termo_ou_analise, str) else None
    extra = ""
    if item is None and isinstance(termo_ou_analise, dict):
        fracos = mais_fracos(termo_ou_analise, 1)
        item = habilidade(fracos[0][0]) if fracos else None
        if item and fracos:
            extra = f"É o ponto mais fraco do projeto avaliado ({fracos[0][1]['nota']}/100). Comece por: {fracos[0][1]['sugestoes'][0]}\n\n"
    if item is None:
        return "Diga qual habilidade quer evoluir. " + visao_geral()
    estudar = []
    for ref in item["estudar"]:
        achado = logica.concept(ref) or conhecimento.lookup(ref)
        if achado:
            estudar.append(achado["nome"])
    return (f"**Plano para evoluir: {item['nome']}**\n{extra}"
            f"1. Releia o checklist (peça \"checklist de {item['nome'].lower()}\") e marque o que você já faz.\n"
            f"2. Estude (peça \"explique <tema>\"): {', '.join(estudar) or 'prática direta'}.\n"
            f"3. **Treino da semana:** {item['treino']}\n"
            "4. Depois, avalie de novo um projeto seu e confira se a nota subiu.")


def treino_da_semana(hoje: date | None = None) -> str:
    """Uma habilidade por semana, em rodízio pelas 18: a prática pequena e constante que faz evoluir sempre."""
    semana = (hoje or date.today()).isocalendar()[1]
    item = catalogo()[semana % len(catalogo())]
    return f"**Treino da semana: {item['nome']}**\n\n" + plano(item["id"])


def visao_geral() -> str:
    linhas = [f"- **{h['nome']}**" + (" (medido automaticamente)" if h["medida"] else "") + f": {h['resumo']}" for h in catalogo()]
    return "**Habilidades de programador que eu acompanho:**\n" + "\n".join(linhas)
