"""Números por extenso em português do Brasil (cardinais e ordinais), sem dependências."""

from __future__ import annotations

_UNID = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze",
         "doze", "treze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
_DEZ = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
_CENT = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos",
         "oitocentos", "novecentos"]
_ESCALAS = [("mil", "mil"), ("milhão", "milhões"), ("bilhão", "bilhões"), ("trilhão", "trilhões")]
_ORD = {1: "primeiro", 2: "segundo", 3: "terceiro", 4: "quarto", 5: "quinto", 6: "sexto", 7: "sétimo",
        8: "oitavo", 9: "nono", 10: "décimo"}
LIMITE = 10**15  # acima disso (ou com zeros à esquerda) lê-se dígito a dígito


def _ate_999(n: int, feminino: bool) -> str:
    if n == 100:
        return "cem"
    c, resto = divmod(n, 100)
    partes = []
    if c:
        partes.append(_CENT[c][:-2] + "as" if feminino and c >= 2 else _CENT[c])
    if resto < 20:
        if resto or not c:
            partes.append(_feminino(resto) if feminino else _UNID[resto])
    else:
        d, u = divmod(resto, 10)
        partes.append(_DEZ[d] + (" e " + (_feminino(u) if feminino else _UNID[u]) if u else ""))
    return " e ".join(partes)


def _feminino(n: int) -> str:
    return {1: "uma", 2: "duas"}.get(n, _UNID[n])


def por_extenso(n: int, feminino: bool = False) -> str:
    """1234 -> "mil duzentos e trinta e quatro". Negativos levam "menos"."""
    if n < 0:
        return "menos " + por_extenso(-n, feminino)
    if n >= LIMITE:
        return " ".join(_UNID[int(d)] for d in str(n))
    if n < 1000:
        return _ate_999(n, feminino)
    grupos: list[int] = []
    while n:
        n, g = divmod(n, 1000)
        grupos.append(g)
    partes: list[str] = []
    ultimo = 0
    for i in range(len(grupos) - 1, -1, -1):
        g = grupos[i]
        if not g:
            continue
        ultimo = g
        if i == 0:
            texto = _ate_999(g, feminino)
        elif i == 1:
            texto = "mil" if g == 1 else _ate_999(g, feminino) + " mil"
        else:
            sing, plur = _ESCALAS[i - 1]
            texto = f"um {sing}" if g == 1 else f"{_ate_999(g, False)} {plur}"
        partes.append(texto)
    # "mil e cem", "dois mil e trezentos"; sem "e" quando sobra centena composta ("mil cento e um")
    if len(partes) > 1 and (ultimo < 100 or ultimo % 100 == 0):
        return " ".join(partes[:-1]) + " e " + partes[-1]
    return " ".join(partes)


def digito_a_digito(texto: str) -> str:
    return " ".join(_UNID[int(d)] for d in texto if d.isdigit())


def ordinal(n: int, feminino: bool = False) -> str:
    """1 -> primeiro/primeira; acima de 10 lê o cardinal (forma comum na fala)."""
    if n in _ORD:
        palavra = _ORD[n]
        return palavra[:-1] + "a" if feminino else palavra
    return por_extenso(n, feminino)


def decimal(inteira: str, fracao: str) -> str:
    """"3", "14" -> "três vírgula catorze"; zeros à esquerda da fração são lidos um a um."""
    zeros = len(fracao) - len(fracao.lstrip("0"))
    resto = fracao.lstrip("0")
    cauda = " ".join(["zero"] * zeros + ([por_extenso(int(resto))] if resto else []))
    return f"{numero(inteira)} vírgula {cauda}"


def numero(texto: str, feminino: bool = False) -> str:
    """Dígitos -> extenso. Zero à esquerda ou número gigante (telefone, protocolo) vira dígito a dígito."""
    if len(texto) > 1 and texto.startswith("0") or len(texto) > 15:
        return digito_a_digito(texto)
    return por_extenso(int(texto), feminino)
