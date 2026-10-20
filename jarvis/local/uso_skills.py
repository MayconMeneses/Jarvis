"""Uso de IA no motor local ("quanto gastei", "cota do claude", "uso de IA"): responde sem gastar nenhuma IA."""

from __future__ import annotations

import re
import time

from jarvis.uso import resumo, servico

_PERIODO = (("hoje", r"\bhoje\b"), ("7d", r"\b(semana|7 dias)\b"), ("30d", r"\b30 dias\b"), ("tudo", r"\b(tudo|total|sempre)\b"))


def _periodo(texto: str) -> str:
    return next((p for p, rx in _PERIODO if re.search(rx, texto)), "mes")


def _fmt(n: float) -> str:
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}k" if n >= 1e3 else str(int(n))


def _linha_cota(m: dict, nome: str) -> str:
    if m["pct"] is None:
        return f"- {nome}: {_fmt(m['usado'])} usados (sem teto definido; calibre na janela Uso de IA)."
    extra = " Nesse ritmo acaba antes do reset." if m["acaba_antes_do_reset"] else ""
    return f"- {nome}: cerca de {m['pct']:.0f}% do teto estimado.{extra}"


def responder(texto: str, cfg=None) -> str:
    baixo = texto.lower()
    reg = servico.atualizar(intervalo=5)
    agora = time.time()
    r = resumo.resumo(reg, _periodo(baixo), agora)
    if r["vazio"]:
        return "Ainda não há uso de IA registrado. Assim que o Claude Code ou a Jarvis responderem, os números aparecem aqui."
    cota, orc, t = r["cota"], r["orcamento"], r["totais"]
    if re.search(r"\bcota\b|\blimite\b", baixo):
        return ("Cota do Claude (ESTIMATIVA, o Claude não informa por API):\n" + _linha_cota(cota["janela_5h"], "janela de 5 h")
                + "\n" + _linha_cota(cota["semana"], "semana"))
    linhas = [f"Uso de IA, {r['rotulo']}: {t['msgs']} respostas, {_fmt(t['tout'])} de saída, {_fmt(t['cw'] + t['cr'])} de cache.",
              f"Valor equivalente em API: US$ {t['custo']:.2f}" + (" (estimado pela tabela de preços; a assinatura não cobra por token)." if t["estimado"] else ".")]
    if r["por_modelo"]:
        linhas.append("Por modelo: " + "; ".join(f"{m['nome']} US$ {m['custo']:.2f}" + ("" if m["preco_ok"] else " (sem preço)") for m in r["por_modelo"][:4]) + ".")
    if orc["orcamento"]:
        linhas.append(f"Orçamento do mês: {orc['pct']:.0f}% usado, projeção US$ {orc['projecao']:.2f}.")
    linhas.append(_linha_cota(cota["janela_5h"], "Cota 5 h (estimativa)"))
    if r["locais"]["pct_local"]:
        linhas.append(f"{r['locais']['pct_local']:.0f}% dos pedidos foram resolvidos sem IA.")
    return "\n".join(linhas)
