"""Normalização pt-BR do texto antes da síntese: números, horas, datas, moedas, siglas, unidades e símbolos.

Tudo aqui é função pura (texto entra, texto sai), para testar sem voz nem placa de som.
A ordem importa: primeiro as formas estruturadas (R$, hora, data, %), depois os números soltos.
"""

from __future__ import annotations

import re

from jarvis.voice.numeros import decimal, digito_a_digito, numero, ordinal, por_extenso

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro",
         "outubro", "novembro", "dezembro"]
_NUM = r"\d{1,3}(?:\.\d{3})+|\d+"   # 1.234.567 ou 1234

# sigla -> como falar (a Piper lê "PC" e "CPU" de forma errada ou soletra mal)
SIGLAS = {
    "PC": "pê cê", "CPU": "cê pê u", "GPU": "gê pê u", "RAM": "rám", "SSD": "ésse ésse dê", "HD": "agá dê",
    "USB": "u ésse bê", "IA": "i á", "API": "á pê i", "URL": "u érre éle", "PDF": "pê dê éfe",
    "CPF": "cê pê éfe", "CNPJ": "cê ene pê jota", "SMS": "ésse eme ésse", "GPS": "gê pê ésse",
    "TV": "tê vê", "PIX": "pix", "LGPD": "éle gê pê dê", "MCP": "ême cê pê", "TTS": "tê tê ésse",
    "HTML": "agá tê eme éle", "CSS": "cê ésse ésse", "SQL": "ésse quê éle", "LLM": "éle éle eme",
    "OK": "ôquei", "WI-FI": "uaifai", "WIFI": "uaifai", "ID": "i dê", "E-MAIL": "i-meio",
}
UNIDADES = {  # sigla -> (singular, plural)
    "GB": ("gigabyte", "gigabytes"), "MB": ("megabyte", "megabytes"), "KB": ("quilobyte", "quilobytes"),
    "TB": ("terabyte", "terabytes"), "GHZ": ("gigahertz", "gigahertz"), "MHZ": ("megahertz", "megahertz"),
    "MS": ("milissegundo", "milissegundos"), "KM": ("quilômetro", "quilômetros"),
    "KG": ("quilo", "quilos"), "MIN": ("minuto", "minutos"), "SEG": ("segundo", "segundos"),
    "H": ("hora", "horas"), "M": ("metro", "metros"), "CM": ("centímetro", "centímetros"),
    "MM": ("milímetro", "milímetros"), "G": ("grama", "gramas"), "W": ("watt", "watts"),
}
ABREVIACOES = {
    r"\bDr\.": "doutor", r"\bDra\.": "doutora", r"\bSr\.": "senhor", r"\bSra\.": "senhora",
    r"\bProf\.": "professor", r"\bProfa\.": "professora", r"\bAv\.": "avenida", r"\bTel\.": "telefone",
    r"\bpág\.": "página", r"\bobs\.": "observação", r"\bp\. ?ex\.": "por exemplo", r"\bex\.": "por exemplo",
    r"\bnº\s*": "número ", r"\bn\.º\s*": "número ", r"\bvs\.?": "versus", r"\bporcent\.": "por cento",
    r"\bapt\.": "apartamento", r"\bpq\b\.?": "porque", r"\bvc\b": "você", r"\bvcs\b": "vocês",
}
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3\u2190-\u21FF]+")


def _inteiro(texto: str) -> int:
    return int(texto.replace(".", ""))


def _moeda(m: re.Match) -> str:
    reais = _inteiro(m.group(1))
    centavos = int((m.group(2) or "0").ljust(2, "0")[:2])
    escala = (m.group(3) or "").lower()
    if escala:
        return f"{por_extenso(reais)} {escala} de reais"
    partes = []
    if reais or not centavos:
        partes.append(f"{por_extenso(reais)} {'real' if reais == 1 else 'reais'}")
    if centavos:
        partes.append(f"{por_extenso(centavos)} {'centavo' if centavos == 1 else 'centavos'}")
    return " e ".join(partes)


def _hora_extenso(h: int) -> str:
    return por_extenso(h, feminino=True) if h in (1, 2) else por_extenso(h)


def _hora(m: re.Match) -> str:
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    if h > 23 or mi > 59:
        return m.group(0)
    if h == 0 and mi == 0:
        return "meia-noite"
    if h == 12 and mi == 0:
        return "meio-dia"
    if mi == 0:
        return f"{_hora_extenso(h)} {'hora' if h == 1 else 'horas'}"
    return f"{_hora_extenso(h)} e {por_extenso(mi)}"


def _data(m: re.Match) -> str:
    dia, mes = int(m.group(1)), int(m.group(2))
    if not (1 <= dia <= 31 and 1 <= mes <= 12):
        return m.group(0)
    texto = f"{'primeiro' if dia == 1 else por_extenso(dia)} de {MESES[mes - 1]}"
    ano = m.group(3)
    if ano:
        texto += f" de {por_extenso(int(ano) + (2000 if len(ano) == 2 else 0))}"
    return texto


def _percentual(m: re.Match) -> str:
    valor = decimal(m.group(1).replace(".", ""), m.group(2)) if m.group(2) else numero(m.group(1).replace(".", ""))
    return f"{valor} por cento"


def _com_unidade(m: re.Match) -> str:
    inteira, fracao, sigla = m.group(1).replace(".", ""), m.group(2), m.group(3)
    sing, plur = UNIDADES[sigla.upper()]
    fem = sigla.upper() in ("H", "G")
    valor = decimal(inteira, fracao) if fracao else numero(inteira, fem)
    return f"{valor} {sing if not fracao and int(inteira) == 1 else plur}"


def _decimal(m: re.Match) -> str:
    return decimal(m.group(1).replace(".", ""), m.group(2))


def _ordinal(m: re.Match) -> str:
    return ordinal(int(m.group(1)), feminino=m.group(2) in ("ª", "a"))


def _sigla(m: re.Match) -> str:
    palavra = m.group(0)
    if palavra in SIGLAS:
        return SIGLAS[palavra]
    if palavra.upper() in SIGLAS and palavra.isupper():
        return SIGLAS[palavra.upper()]
    if not re.search(r"[AEIOUÁÉÍÓÚÂÊÔÃÕ]", palavra):  # sem vogal não é pronunciável: soletra
        return " ".join(palavra)
    return palavra


def numeros_e_simbolos(t: str) -> str:
    t = re.sub(rf"R\$\s*({_NUM})(?:,(\d{{1,2}}))?(?:\s+(mil|milhão|milhões|bilhão|bilhões)\b)?", _moeda, t)
    t = re.sub(r"(?<![\d:])(\d{1,2}):(\d{2})(?![\d:])", _hora, t)
    t = re.sub(r"(?<![\d:])(\d{1,2})\s?h(?:(\d{2}))?\b(?!\w)", _hora, t)
    t = re.sub(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{4}|\d{2}))?(?![\d/])", _data, t)
    t = re.sub(rf"({_NUM})(?:,(\d+))?\s?%", _percentual, t)
    t = re.sub(r"(?<![\w.,])(-?)(\d+)\s?[\u00b0\u00ba]\s?C\b",
               lambda m: ("menos " if m.group(1) else "") + numero(m.group(2)) + " graus Celsius", t)
    t = re.sub(r"\b(\d{4,5})-(\d{4})\b", lambda m: digito_a_digito(m.group(1)) + ", " + digito_a_digito(m.group(2)), t)
    unidades = "|".join(sorted(UNIDADES, key=len, reverse=True))
    t = re.sub(rf"(?<![\w.,])({_NUM})(?:,(\d+))?\s?({unidades})\b(?![\w])", _com_unidade, t, flags=re.IGNORECASE)
    t = re.sub(r"(?<![\w.,])(\d+)([ºª])", lambda m: ordinal(int(m.group(1)), m.group(2) == "ª"), t)
    t = re.sub(rf"(?<![\w.,])({_NUM}),(\d+)(?![\d])", _decimal, t)
    t = re.sub(r"(?<![\w.,])(\d{1,3}(?:\.\d{3})+|\d+)(?![\w])", lambda m: numero(m.group(1).replace(".", "")), t)
    return t


def simbolos_e_siglas(t: str) -> str:
    for padrao, troca in ABREVIACOES.items():
        t = re.sub(padrao, troca, t, flags=re.IGNORECASE)
    t = re.sub(r"\be\.g\.", "por exemplo", t)
    t = t.replace("&", " e ").replace("→", ", ").replace("->", ", ").replace("=>", ", ").replace("≥", " maior ou igual a ")
    t = re.sub(r"\s\+\s", " mais ", t)
    t = re.sub(r"\s=\s", " igual a ", t)
    t = re.sub(r"(?<=\w)/(?=\w)", " ", t)
    t = re.sub(r"\b[A-Za-z]:?\\[\w\\.-]+", "um caminho de arquivo", t)  # C:\pasta\arq.txt
    t = re.sub(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕ][A-ZÁÉÍÓÚÂÊÔÃÕ0-9-]{1,}\b", _sigla, t)
    t = re.sub(r"\bwi-?fi\b", "uaifai", t, flags=re.IGNORECASE)
    t = re.sub(r"\be-?mail(s?)\b", lambda m: "i-meio" + m.group(1), t, flags=re.IGNORECASE)
    return t


def limpar_marcacao(t: str) -> str:
    """Markdown, código, links, e-mails, emojis e listas -> texto corrido, com ponto no fim de cada linha."""
    t = re.sub(r"```.*?```", " (código na janela) ", t, flags=re.DOTALL)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", t)        # [texto](url) -> texto
    t = re.sub(r"https?://\S+|www\.\S+", "link", t)
    t = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "um endereço de e-mail", t)
    t = _EMOJI.sub(" ", t)
    t = re.sub(r"^\s*(?:[-•*·▪]|\d{1,2}[.)])\s+", "", t, flags=re.MULTILINE)   # marcadores de lista
    t = re.sub(r"^\s*#{1,6}\s*", "", t, flags=re.MULTILINE)
    t = re.sub(r"^[ \t]*[-=_*]{3,}[ \t]*$", "", t, flags=re.MULTILINE)          # linhas horizontais
    t = re.sub(r"(?<![\w$])[*_#>|~]+|[*_~|]+(?![\w])", "", t)
    t = re.sub(r"(?<=[^\s.!?…:;,])[ \t]*\n+", ". ", t)   # quebra de linha sem pontuação vira pausa
    return t


def pausas(t: str) -> str:
    """Pontuação que ajuda a cadência: travessão e parênteses viram vírgula, repetições são colapsadas."""
    t = re.sub(r"\s[—–-]\s", ", ", t)
    t = re.sub(r"\s*[()\[\]{}]\s*", ", ", t)
    t = re.sub(r"\.{3,}|…", "…", t)
    t = re.sub(r"([!?]){2,}", r"\1", t)
    t = re.sub(r"\s+([,.;:!?…])", r"\1", t)
    t = re.sub(r",\s*(?=[,.;:!?])", "", t)
    t = re.sub(r"([.!?…:;]),", r"\1", t)
    t = re.sub(r"^[,\s]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def normalizar(texto: str) -> str:
    """Texto já sem marcação -> texto pronto para a Piper/edge-tts."""
    return pausas(simbolos_e_siglas(numeros_e_simbolos(texto)))
