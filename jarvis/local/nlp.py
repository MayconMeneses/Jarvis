"""Texto em português para o casador de intenções: normalização, stopwords, radicais, erros de digitação e n-gramas.

Tudo local e sem IA. O radical vem do snowballstemmer (já é dependência do projeto).
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Palavras sem valor para casar intenção. "nao" e "como" ficam de fora de propósito: carregam sentido ("não ouço", "como instalar").
STOPWORDS = frozenset("""a o as os um uma uns umas de do da dos das em no na nos nas por pelo pela para pra pro com sem sobre ao aos
e ou que se meu minha meus minhas seu sua teu tua me te lhe mim ti eu tu ele ela ja so ate la ai aqui isso isto esse essa
este esta esses essas aquele aquela mais muito muita bem tambem entao pois mas quando qual quais foi ser sao era tem ter tenho
pode posso poderia quero queria gostaria preciso gosto vou vai estou esta estao estar favor pfv pf
ei ok oi ola hey tipo assim coisa""".split())

# Variações comuns de fala e escrita levadas a uma palavra só (antes do radical).
SINONIMOS = {
    "telefone": "celular", "smartphone": "celular", "aparelho": "celular", "cel": "celular", "mobile": "celular", "fone": "celular",
    "ipad": "celular", "iphone": "iphone", "ios": "iphone", "apple": "iphone", "safari": "iphone",
    "droid": "android",
    "javis": "jarvis", "jarvs": "jarvis", "jarves": "jarvis", "jarbis": "jarvis", "jarvi": "jarvis", "garvis": "jarvis", "jarvez": "jarvis",
    "senha": "chave", "token": "chave", "api": "chave",
    "microfone": "escuta", "mic": "escuta", "ouvir": "escuta", "ouvindo": "escuta", "ouve": "escuta", "ouco": "escuta",
    "escutar": "escuta", "escutando": "escuta", "escuta": "escuta",
    "falar": "voz", "fala": "voz", "falando": "voz", "som": "voz", "audio": "voz",
    "backup": "copia", "seguranca": "copia", "exportar": "copia", "salvar": "copia",
    "importar": "restaurar", "recuperar": "restaurar", "migrar": "levar", "transferir": "levar", "passar": "levar", "trocar": "levar",
    "remover": "desinstalar", "excluir": "desinstalar",
    "baixar": "instalar", "colocar": "instalar", "botar": "instalar",
    "versao": "atualizar", "update": "atualizar", "novidade": "atualizar", "atualizacao": "atualizar",
    "cor": "tema", "cores": "tema", "visual": "tema", "aparencia": "tema", "escuro": "tema", "claro": "tema",
    "janelas": "caixas", "janela": "caixas", "paineis": "caixas", "painel": "caixas", "cartoes": "caixas",
    "calendario": "agenda", "compromissos": "agenda", "gmail": "email", "emails": "email", "mail": "email", "outlook": "email",
    "travando": "travar", "trava": "travar", "travou": "travar", "lenta": "lento", "lerda": "lento", "demora": "lento", "demorando": "lento",
    "bug": "erro", "problema": "erro", "falha": "erro", "falhou": "erro", "quebrou": "erro", "defeito": "erro",
    "limite": "cota", "gasto": "cota", "gastei": "cota",
    "noticia": "noticias", "manchetes": "noticias", "ia": "ia", "inteligencia": "ia",
}
_stem = None


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def palavras(text: str) -> list[str]:
    """Palavras sem acento, minúsculas, sem pontuação. "wi-fi" vira "wifi"; "e-mail", "email"."""
    texto = re.sub(r"(?<=[a-z])-(?=[a-z])", "", fold(text))
    return re.findall(r"[a-z0-9]+", texto)


_sin_radicais: dict[str, str] | None = None


def _radical(p: str) -> str:
    """Radical da palavra; sinônimos valem também para as outras flexões ("baixar" e "baixo" viram o mesmo radical de "instalar")."""
    global _stem, _sin_radicais
    if _stem is None:
        import snowballstemmer

        _stem = snowballstemmer.stemmer("portuguese")
        _sin_radicais = {_stem.stemWord(k): _stem.stemWord(v) for k, v in SINONIMOS.items() if k != v and len(k) >= 4}
    r = _stem.stemWord(SINONIMOS.get(p, p))
    return _sin_radicais.get(r, r)


@lru_cache(maxsize=8192)
def radical(p: str) -> str:
    return _radical(p)


def distancia(a: str, b: str) -> int:
    """Distância de Damerau-Levenshtein (troca de letras vizinhas conta 1: "celualr" ~ "celular")."""
    if abs(len(a) - len(b)) > 3:
        return 99
    anterior2, anterior = None, list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        atual = [i]
        for j, cb in enumerate(b, 1):
            custo = 0 if ca == cb else 1
            v = min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + custo)
            if anterior2 is not None and i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                v = min(v, anterior2[j - 2] + 1)
            atual.append(v)
        anterior2, anterior = anterior, atual
    return anterior[-1]


def corrigir(palavra: str, vocabulario: frozenset[str] | set[str]) -> str:
    """Troca uma palavra desconhecida pela mais próxima do vocabulário (1 erro até 6 letras, 2 acima). Curtas ficam como estão."""
    if palavra in vocabulario or len(palavra) < 4 or palavra.isdigit():
        return palavra
    limite = 1 if len(palavra) <= 6 else 2
    melhor, melhor_d = palavra, limite + 1
    for candidata in vocabulario:
        if abs(len(candidata) - len(palavra)) > limite or candidata[0] != palavra[0] and limite == 1 and len(palavra) <= 4:
            continue
        d = distancia(palavra, candidata)
        if d < melhor_d or (d == melhor_d and d <= limite and candidata < melhor):
            melhor, melhor_d = candidata, d
    return melhor if melhor_d <= limite else palavra


def termos(text: str, vocabulario: frozenset[str] | set[str] = frozenset()) -> list[str]:
    """Radicais úteis do texto (sem stopwords), com erros de digitação corrigidos pelo vocabulário conhecido."""
    saida = []
    for p in palavras(text):
        if vocabulario:
            p = corrigir(p, vocabulario)
        if p in STOPWORDS:
            continue
        saida.append(radical(p))
    return saida


def trigramas(text: str) -> set[str]:
    base = " " + " ".join(palavras(text)) + " "
    return {base[i:i + 3] for i in range(len(base) - 2)}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0
