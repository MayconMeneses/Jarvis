"""Nota de 0 a 100 de cada artigo, sempre com os motivos (no molde de info/jobs.score).

  +40 relevância (palavras-chave do nicho; o título pesa mais que o resumo)
  +20 nota da fonte (0–10 × 2)
  +15 ineditismo (nenhum título parecido no histórico recente)
  +15 impacto (dinheiro, lei, tecnologia central ou quem você acompanha)
  +10 frescor (linear dentro da janela)
  -30 clickbait, listicle ou release disfarçado
"""

from __future__ import annotations

import re
import time

from jarvis.radar.dedup import _sem_acento, parecidos
from jarvis.radar.modelos import Artigo

IMPACTO = ("lei", "decreto", "aprova", "aprovou", "proibe", "regulament", "multa", "bilhao", "bilhoes", "milhoes",
           "lanca", "lancou", "anuncia", "anunciou", "acordo", "fusao", "aquisicao", "compra", "falencia", "vazamento",
           "ataque", "investigacao", "decisao", "recorde", "queda", "alta", "juros", "inflacao")
CLICKBAIT = re.compile(
    r"voce nao vai acreditar|veja o que|saiba (o que|como|quem)|descubra|confira|chocante|bomba|inacreditavel|"
    r"^\s*(top\s*)?\d+\s+(coisas|motivos|dicas|jeitos|formas|razoes|segredos|erros|filmes|series|apps)\b|"
    r"\b\d+\s+(coisas|motivos|dicas|jeitos|formas|razoes|segredos)\b|isso (vai|muda)|nunca mais|em (apenas )?\d+ passos|"
    r"comunicado a imprensa|press release|release", re.I)
PATROCINADO = re.compile(r"publieditorial|patrocinad|conteudo (de marca|publicitario)|\[publi\]|oferta|cupom|promocao|desconto", re.I)


def _tem(texto: str, termo: str) -> bool:
    termo = _sem_acento(termo).strip()
    return bool(termo) and re.search(rf"(?<![a-z0-9]){re.escape(termo)}", texto) is not None


def eh_patrocinado(artigo: Artigo) -> bool:
    return PATROCINADO.search(_sem_acento(f"{artigo.titulo} {artigo.resumo[:120]}")) is not None


def pontuar(artigo: Artigo, palavras_chave: list[str], entidades: list[str], janela_horas: int,
            titulos_recentes: list[str], agora: float | None = None) -> tuple[int, list[str]]:
    agora = agora if agora is not None else time.time()
    titulo, resumo = _sem_acento(artigo.titulo), _sem_acento(artigo.resumo)
    pontos, motivos = 0, []

    no_titulo = [p for p in palavras_chave if _tem(titulo, p)]
    no_resumo = [p for p in palavras_chave if p not in no_titulo and _tem(resumo, p)]
    relevancia = min(40, 16 * len(no_titulo) + 8 * len(no_resumo))
    if relevancia:
        pontos += relevancia
        motivos.append("bate com: " + ", ".join(no_titulo + no_resumo))

    fonte = round(max(0.0, min(10.0, artigo.nota_fonte)) * 2)
    pontos += fonte
    motivos.append(f"fonte {artigo.fonte} (nota {artigo.nota_fonte:g})")

    if not any(parecidos(artigo.titulo, antigo) for antigo in titulos_recentes):
        pontos += 15
        motivos.append("assunto inédito")

    texto = f"{titulo} {resumo}"
    impacto = [w for w in IMPACTO if _tem(texto, w)]
    seguidas = [e for e in entidades if _tem(texto, e)]
    ganho = min(15, 5 * len(impacto) + 8 * len(seguidas))
    if ganho:
        pontos += ganho
        motivos.append("impacto: " + ", ".join(seguidas + impacto[:3]))

    if artigo.quando:
        idade_h = max(0.0, (agora - artigo.quando) / 3600)
        pontos += round(10 * max(0.0, 1 - idade_h / max(1, janela_horas)))
    if CLICKBAIT.search(titulo):
        pontos -= 30
        motivos.append("cara de clickbait/lista/release (-30)")
    return max(0, min(100, pontos)), motivos
