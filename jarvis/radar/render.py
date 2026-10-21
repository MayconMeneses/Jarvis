"""Boletim → Markdown e HTML (arquivo único, sem JavaScript). Todo texto vem de terceiros: tudo é escapado.

Só links http(s) viram links clicáveis. O HTML leva uma política de segurança (CSP) que proíbe script e rede.
"""

from __future__ import annotations

import html
from datetime import datetime

from jarvis.radar.feed_parse import link_valido
from jarvis.radar.modelos import Boletim, Item

SEM_IA = ("_Resumos extrativos: frases do próprio texto da fonte. Sem IA não há manchete própria, tradução de jargão, "
          "ângulo, conexões nem comparação entre fontes: isso é omitido, nunca inventado._")


def _data(item: Item) -> str:
    return datetime.fromtimestamp(item.artigo.quando).strftime("%d/%m") if item.artigo.quando else "sem data"


def _meta(item: Item) -> str:
    partes = [item.artigo.fonte, _data(item)]
    if item.origem == "artigo" and item.palavras:
        partes.append(f"leitura {max(1, round(item.palavras / 200))} min")
    else:
        partes.append("resumo baseado só no RSS")
    partes.append(f"[{item.rotulo}]")
    return " · ".join(partes)


def cabecalho(b: Boletim) -> list[str]:
    linhas = [f"Data: {b.dia} · Nicho: {b.nicho} · Artigos varridos: {b.varridos} · Modo: {'com IA' if b.com_ia else 'sem IA'}"]
    linhas.append("Fontes que falharam: " + ("; ".join(b.falhas) if b.falhas else "nenhuma"))
    linhas += [f"Aviso: {a}" for a in b.avisos]
    if b.atrasado:
        linhas.append("Aviso: este é o boletim atrasado de hoje (o computador estava desligado no horário).")
    return linhas


def markdown(b: Boletim) -> str:
    out = [f"# Radar de {b.nicho} — {b.dia}", ""] + [f"- {l}" for l in cabecalho(b)] + [""]
    if not b.com_ia:
        out += [SEM_IA, ""]
    for n, item in enumerate(b.itens, 1):
        out += [f"## {n}. {item.manchete}", f"*{_meta(item)}* · nota {item.nota}/100"]
        if item.suspeito:
            out += [f"⚠ Este item tem texto que tenta dar ordens à IA ({item.suspeito}). Mostrado só com o título; abra por sua conta e risco."]
        out += [f"- {l}" for l in item.linhas]
        if b.com_ia and item.por_que:
            out += [f"**Por que isso importa:** {item.por_que}"]
        elif item.por_que and not item.suspeito:
            out += [f"_{item.por_que}_"]
        if b.com_ia and item.jargao:
            out += [f"**Tradução do jargão:** {item.jargao}"]
        if b.com_ia and item.angulo:
            out += [f"**Ângulo para usar:** {item.angulo}"]
        if item.tambem_em:
            out += [f"Também em: {', '.join(item.tambem_em)}"]
        out += [f"Link: {item.artigo.link}" if link_valido(item.artigo.link) else "Link indisponível", ""]
    if b.conexoes:
        out += ["## Conexões do dia"] + [f"- {c}" for c in b.conexoes] + [""]
    if b.observar:
        out += ["## O que observar amanhã"] + [f"- {o}" for o in b.observar] + [""]
    if not b.itens:
        out += ["Nenhum item passou nos filtros hoje.", ""]
    return "\n".join(out)


CSS = ("body{font:16px/1.55 system-ui,sans-serif;max-width:46rem;margin:2rem auto;padding:0 1rem;background:#0b1118;color:#dbe7f3}"
       "h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.6rem}a{color:#5bd4ff}.meta{color:#8aa3b8;font-size:.9rem}"
       ".aviso{background:#3a2a10;padding:.5rem .8rem;border-radius:.4rem}.nota{color:#8aa3b8}li{margin:.25rem 0}"
       "@media(prefers-color-scheme:light){body{background:#fff;color:#14202b}a{color:#0a64a0}.meta,.nota{color:#52687a}}")


def _e(texto: str) -> str:
    return html.escape(texto, quote=True)


def pagina(b: Boletim) -> str:
    corpo = [f"<h1>Radar de {_e(b.nicho)} — {_e(b.dia)}</h1>", "<ul class='meta'>" + "".join(f"<li>{_e(l)}</li>" for l in cabecalho(b)) + "</ul>"]
    if not b.com_ia:
        corpo.append(f"<p class='nota'>{_e(SEM_IA.strip('_'))}</p>")
    for n, item in enumerate(b.itens, 1):
        corpo.append(f"<h2>{n}. {_e(item.manchete)}</h2><p class='meta'>{_e(_meta(item))} · nota {item.nota}/100</p>")
        if item.suspeito:
            corpo.append(f"<p class='aviso'>⚠ Texto que tenta dar ordens à IA: {_e(item.suspeito)}. Mostrado só com o título.</p>")
        if item.linhas:
            corpo.append("<ul>" + "".join(f"<li>{_e(l)}</li>" for l in item.linhas) + "</ul>")
        if item.por_que and not item.suspeito:
            corpo.append(f"<p>{'<strong>Por que isso importa:</strong> ' if b.com_ia else ''}{_e(item.por_que)}</p>")
        for rotulo, texto in ((("Tradução do jargão", item.jargao), ("Ângulo para usar", item.angulo)) if b.com_ia else ()):
            if texto:
                corpo.append(f"<p><strong>{rotulo}:</strong> {_e(texto)}</p>")
        if item.tambem_em:
            corpo.append(f"<p class='meta'>Também em: {_e(', '.join(item.tambem_em))}</p>")
        if link_valido(item.artigo.link):
            corpo.append(f"<p><a href='{_e(item.artigo.link)}' rel='noopener noreferrer' target='_blank'>Abrir a matéria</a></p>")
    for titulo, lista in (("Conexões do dia", b.conexoes), ("O que observar amanhã", b.observar)):
        if lista:
            corpo.append(f"<h2>{titulo}</h2><ul>" + "".join(f"<li>{_e(x)}</li>" for x in lista) + "</ul>")
    csp = "default-src 'none'; style-src 'unsafe-inline'; img-src 'none'; base-uri 'none'; form-action 'none'"
    return (f"<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><meta http-equiv='Content-Security-Policy' content=\"{csp}\">"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'><title>Radar de {_e(b.nicho)} — {_e(b.dia)}</title>"
            f"<style>{CSS}</style></head><body>{''.join(corpo)}</body></html>")
