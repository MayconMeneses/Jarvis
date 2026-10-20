"""Analista de conteúdo do Instagram: métricas calculadas por código, nunca estimadas pela IA.

Fluxo: importar (CSV, JSON ou texto colado) -> higiene -> métricas -> relatório -> rodadas (comparação).
Os dados vêm de pesquisas públicas na web (só o que é público) e do que o usuário importa; a Jarvis NUNCA acessa
o Instagram logada nem raspa o site (viola os termos). Onde falta número, o relatório mostra "n/d" e o motivo.
Legenda é dado de terceiros: fica como texto inerte (no máximo 200 caracteres), nunca vira instrução.

Um post é um dict (igual no celular, que repete estas fórmulas em movel/js/instagram-*.js):
perfil, link, data, formato, legenda, likes, comentarios, views, salvamentos, compartilhamentos (None = não informado).
Os casos de teste compartilhados com o celular ficam em tests/dados/instagram_casos.json.
"""

from __future__ import annotations

import unicodedata

PESOS_PADRAO = {"salvamentos": 3, "compartilhamentos": 3, "comentarios": 2, "likes": 1}
HORAS_MADURO = 48          # antes disso o post ainda está ganhando alcance: fica fora das medianas
MIN_POSTS_PERFIL = 6       # abaixo disso o perfil tem "baixa confiança"
MIN_POSTS_GRUPO = 3        # mínimo de posts do mesmo perfil e formato para ter mediana e outlier
LIMITE_OUTLIER = 2.0       # engajamento / mediana do (perfil, formato)
LIMITE_COMENTARIO_PCT = 30  # taxa de comentário >= 0,30 (comparada em inteiros, sem erro de ponto flutuante)
MAX_LEGENDA = 200          # só o começo da legenda é guardado
CAMPOS_NUMERICOS = ("likes", "comentarios", "views", "salvamentos", "compartilhamentos")


def fold(texto: object) -> str:
    """Minúsculas e sem acento (mesma regra de movel/js/util.js)."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower()) if unicodedata.category(c) != "Mn")
