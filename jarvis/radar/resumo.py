"""Resumo SEM IA: título limpo, lead e frases com número/data do próprio texto, rótulos de origem e "por que entrou".

Regras: nunca mais de 3 frases copiadas por item, cada uma curta e com a fonte ao lado no boletim; sem IA não há
manchete própria, ângulo nem tradução de jargão (isso é omitido, não inventado). Rótulos só dizem o que dá para
saber: [opinião] por sinais do endereço/categoria, [possível paywall] por heurística, senão [não classificado].
"""

from __future__ import annotations

import re

from jarvis.local import websearch
from jarvis.radar import rede, sanear
from jarvis.radar.modelos import Item

MAX_FRASES = 3
MAX_FRASE = 240
_SUFIXO = re.compile(r"\s+[-–—|]\s+[^-–—|]{2,40}$")
_OPINIAO = re.compile(r"/(opiniao|opinion|opinioes|coluna|colunas|colunistas|editorial|blog|artigo-de-opiniao)/", re.I)
_PAYWALL = re.compile(r"assine para|conteudo exclusivo|exclusivo para assinantes|ja e assinante|subscribe to (continue|read)|paywall|"
                      r"assinantes? (podem|tem acesso)", re.I)


def manchete_limpa(titulo: str, fonte: str) -> str:
    """Tira o " - Veículo" do fim quando o título veio com ele."""
    return _SUFIXO.sub("", titulo).strip() if fonte.lower()[:6] in titulo.lower()[-45:] else titulo.strip()


def rotulo_de(item: Item, paywall: bool) -> str:
    a = item.artigo
    if paywall:
        return "possível paywall"
    if _OPINIAO.search(a.link) or any("opini" in c.lower() or "coluna" in c.lower() for c in a.categorias):
        return "opinião"
    return "não classificado"


def parece_paywall(texto: str, resumo_do_feed: str) -> bool:
    dobrado = sanear._sem_acento(texto)
    return bool((_PAYWALL.search(dobrado) and len(texto) < 1500) or (len(texto) < 300 and len(resumo_do_feed) >= 150))


def ler_pagina(link: str, baixar=rede.baixar, robots=rede.robots_permite) -> tuple[str, str]:
    """(texto, estado): lida | robots | erro. Respeita o robots.txt e passa pela rede segura."""
    if not robots(link):
        return "", "robots"
    try:
        dados, tipo = baixar(link, rede.LIMITE_PAGINA)
        if tipo and "html" not in tipo.lower() and "text" not in tipo.lower():
            return "", "erro"
        parser = websearch._TextParser()
        parser.feed(rede.decodificar(dados, tipo))
        return sanear.limpar_terceiros("\n".join(parser.blocks), 4000), "lida"
    except Exception:
        return "", "erro"


def _frases(texto: str) -> list[str]:
    achadas = websearch.sentences(texto)
    return achadas or ([texto.strip()] if len(texto.strip()) >= 20 else [])


def _curta(frase: str) -> str:
    return frase if len(frase) <= MAX_FRASE else frase[:MAX_FRASE].rsplit(" ", 1)[0] + "…"


def escolher_frases(texto: str) -> list[str]:
    """Lead (até 2 frases) + a frase seguinte com mais números/datas. No máximo 3 no total."""
    todas = _frases(texto)
    escolhidas = todas[:2]
    resto = [f for f in todas[2:] if re.search(r"\d", f)]
    if resto:
        escolhidas.append(max(resto, key=lambda f: len(re.findall(r"\d+", f))))
    return [_curta(f) for f in escolhidas[:MAX_FRASES]]


def por_que_entrou(motivos: list[str]) -> str:
    return "Entrou na lista porque " + "; ".join(m for m in motivos if "clickbait" not in m) + "."


def resumir(item: Item, texto_pagina: str = "", paywall: bool = False) -> Item:
    """Preenche o item sem IA. Texto que tenta dar ordens (injeção) é marcado ⚠ e não é resumido."""
    a = item.artigo
    item.manchete = manchete_limpa(a.titulo, a.fonte)
    item.por_que = por_que_entrou(item.motivos)
    item.rotulo = rotulo_de(item, paywall)
    motivo = sanear.suspeito(f"{a.titulo}\n{a.resumo}\n{texto_pagina[:2000]}")
    if motivo:
        item.suspeito, item.linhas = motivo, []
        return item
    usar_pagina = bool(texto_pagina) and not paywall
    item.origem = "artigo" if usar_pagina else "rss"
    item.palavras = len(texto_pagina.split()) if usar_pagina else 0
    item.linhas = escolher_frases(texto_pagina if usar_pagina else a.resumo)
    item.texto_fonte = (texto_pagina if usar_pagina else a.resumo)[:3000]
    return item


def fundamentado(saida: str, fonte: str) -> tuple[bool, list[str]]:
    """Todo número e todo nome próprio de um texto gerado precisa existir no texto-fonte (barreira contra invenção)."""
    base = sanear._sem_acento(fonte)
    faltando = []
    for numero in re.findall(r"\d[\d.,]*\d|\d", saida):
        if numero.rstrip(".,") not in fonte and numero.replace(".", "").replace(",", "") not in base.replace(".", "").replace(",", ""):
            faltando.append(numero)
    for frase in re.split(r"(?<=[.!?])\s+", saida):
        for palavra in re.findall(r"(?<!^)(?<=\s)[A-ZÀ-Ú][\wÀ-ú]{2,}", frase):
            if sanear._sem_acento(palavra) not in base:
                faltando.append(palavra)
    return not faltando, faltando
