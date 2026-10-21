"""Texto escrito → texto para falar, em português do Brasil: números, dinheiro, porcentagem, datas e siglas por extenso.

A voz lê o que está escrito; "R$ 1,2 bilhão" e "30%" soam errados se forem lidos como vêm. Tudo aqui é puro (sem rede).
"""

from __future__ import annotations

import re

_UNID = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze",
         "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
_DEZ = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
_CEM = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
_ESCALAS = [(10**12, "trilhão", "trilhões"), (10**9, "bilhão", "bilhões"), (10**6, "milhão", "milhões")]
PRONUNCIAVEIS = {"PIX", "ONU", "NASA", "OPEP", "BRICS", "SUS", "FIFA", "UNESCO", "OTAN", "UOL", "ENEM", "PROCON"}
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")


def _ate_999(n: int) -> str:
    if n == 100:
        return "cem"
    if n < 20:
        return _UNID[n]
    if n < 100:
        dez, uni = divmod(n, 10)
        return _DEZ[dez] + (f" e {_UNID[uni]}" if uni else "")
    cen, resto = divmod(n, 100)
    return _CEM[cen] + (f" e {_ate_999(resto)}" if resto else "")


def por_extenso(n: int) -> str:
    """0 a 999 trilhões. "mil" sem "um"; "e" antes da última parte quando ela é menor que 100 ou centena redonda."""
    if n < 0:
        return "menos " + por_extenso(-n)
    if n < 1000:
        return _ate_999(n)
    partes: list[tuple[str, int]] = []  # (texto, valor numérico da parte)
    for valor, singular, plural in _ESCALAS:
        if n >= valor:
            q, n = divmod(n, valor)
            partes.append((f"{_ate_999(q)} {singular if q == 1 else plural}", q * valor))
    if n >= 1000:
        mil, n = divmod(n, 1000)
        partes.append(("mil" if mil == 1 else f"{_ate_999(mil)} mil", mil * 1000))
    if n:
        partes.append((_ate_999(n), n))
    textos, ultimo = [p[0] for p in partes], partes[-1][1]
    if len(textos) == 1:
        return textos[0]
    # "e" antes da última parte quando ela é menor que 100 ou centena/milhar redondos: "mil e quinhentos"
    return " ".join(textos[:-1]) + (" e " if ultimo < 100 or ultimo % 100 == 0 else " ") + textos[-1]


def _inteiro(texto: str) -> int:
    return int(texto.replace(".", ""))


def decimal_falado(inteiro: str, fracao: str) -> str:
    """"1,2" → "um vírgula dois"; "3,14" → "três vírgula catorze"; "0,05" → "zero vírgula zero cinco"."""
    parte = por_extenso(_inteiro(inteiro)) + " vírgula "
    if fracao.startswith("0") or len(fracao) > 2:
        return parte + " ".join(_UNID[int(d)] for d in fracao)
    return parte + por_extenso(int(fracao))


def _numero(m: re.Match) -> str:
    inteiro, fracao = m.group(1), m.group(2)
    return decimal_falado(inteiro, fracao) if fracao else por_extenso(_inteiro(inteiro))


def _dinheiro(m: re.Match) -> str:
    valor, escala = m.group(1), (m.group(2) or "").strip().lower()
    inteiro, _, fracao = valor.partition(",")
    if escala:
        falado = decimal_falado(inteiro, fracao) if fracao else por_extenso(_inteiro(inteiro))
        return f"{falado} {escala} de reais"
    reais = _inteiro(inteiro)
    texto = f"{por_extenso(reais)} {'real' if reais == 1 else 'reais'}"
    if fracao and int(fracao) > 0:
        centavos = int((fracao + "0")[:2])
        texto += f" e {por_extenso(centavos)} {'centavo' if centavos == 1 else 'centavos'}"
    return texto


def _sigla(m: re.Match) -> str:
    sigla = m.group(0)
    return sigla if sigla in PRONUNCIAVEIS or len(sigla) > 5 else "-".join(sigla.lower())


def falar_texto(texto: str) -> str:
    """Limpa e converte. Nunca sobra URL, Markdown, emoji, colchete, hashtag ou a palavra "bullet"."""
    t = re.sub(r"https?://\S+|www\.\S+", " ", texto)
    t = _EMOJI.sub(" ", t)
    t = re.sub(r"\[[^\]]*\]|\([^)]*https?[^)]*\)", " ", t)
    t = re.sub(r"[*_`#>|~]+|^\s*[-•]\s+", " ", t, flags=re.M)
    t = re.sub(r"\bbullets?\b", " ", t, flags=re.I)
    t = re.sub(r"R\$\s*(\d[\d.]*(?:,\d+)?)(\s*(?:mil|milh[ãa]o|milh[õo]es|bilh[ãa]o|bilh[õo]es|trilh[ãa]o|trilh[õo]es))?\b", _dinheiro, t, flags=re.I)
    t = re.sub(r"(\d[\d.]*)(?:,(\d+))?\s*%", lambda m: _numero(m) + " por cento", t)
    t = re.sub(r"\b(\d{1,2})/(\d{1,2})\b", lambda m: f"{por_extenso(int(m.group(1)))} de {_MESES[int(m.group(2)) - 1]}"
               if 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(1)) <= 31 else m.group(0), t)
    t = re.sub(r"\b(\d{1,2})º\b", lambda m: "primeiro" if m.group(1) == "1" else por_extenso(int(m.group(1))), t)
    t = re.sub(r"\b(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d+))?\b", _numero, t)
    t = re.sub(r"\b[A-ZÀ-Ú]{2,5}\b", _sigla, t)
    return re.sub(r"\s+", " ", t).strip()
