"""Ferramentas de cálculo do cinto: data/hora por fuso, calculadora segura (AST, sem eval) e conversão de unidades."""

from __future__ import annotations

import ast
import math
import operator
import re
from datetime import datetime

DIAS = ("segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo")
_FUSO = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,2}$")


def hora_data(fuso: str = "") -> str:
    """Data e hora agora, no fuso pedido (nome IANA, ex.: America/Sao_Paulo) ou no do PC."""
    from jarvis.agenda import tz

    zona = None
    if fuso:
        if not _FUSO.match(fuso):
            raise ValueError("fuso inválido; use um nome como America/Sao_Paulo ou Europe/Lisbon")
        zona = tz.resolver(fuso)
        if zona is None:
            raise ValueError(f"não conheço o fuso '{fuso[:40]}'")
    agora = datetime.now(zona or tz.local())
    nome = fuso or str(agora.tzname() or "fuso do PC")
    return f"{DIAS[agora.weekday()]}, {agora:%d/%m/%Y %H:%M} ({nome}, UTC{agora:%z})"


# ── calculadora ──────────────────────────────────────────────────────────
_BINARIOS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
             ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Pow: operator.pow}
_UNARIOS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCOES = {"sqrt": math.sqrt, "abs": abs, "round": round, "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "log": math.log, "log10": math.log10, "exp": math.exp, "floor": math.floor, "ceil": math.ceil}
_CONSTANTES = {"pi": math.pi, "e": math.e}
MAX_EXPRESSAO, MAX_NOS, MAX_EXPOENTE = 200, 60, 1000


def _avaliar(no: ast.AST, contador: list[int]) -> float:
    contador[0] += 1
    if contador[0] > MAX_NOS:
        raise ValueError("expressão complicada demais")
    if isinstance(no, ast.Constant) and type(no.value) in (int, float):
        if abs(no.value) > 1e15:
            raise ValueError("número grande demais")
        return no.value
    if isinstance(no, ast.Name) and no.id in _CONSTANTES:
        return _CONSTANTES[no.id]
    if isinstance(no, ast.UnaryOp) and type(no.op) in _UNARIOS:
        return _UNARIOS[type(no.op)](_avaliar(no.operand, contador))
    if isinstance(no, ast.BinOp) and type(no.op) in _BINARIOS:
        a, b = _avaliar(no.left, contador), _avaliar(no.right, contador)
        if isinstance(no.op, ast.Pow) and (abs(b) > MAX_EXPOENTE or (abs(a) > 1e6 and abs(b) > 50)):
            raise ValueError("potência grande demais")
        return _BINARIOS[type(no.op)](a, b)
    if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id in _FUNCOES and not no.keywords:
        if not 1 <= len(no.args) <= 2:
            raise ValueError("função com argumentos demais")
        return _FUNCOES[no.func.id](*(_avaliar(a, contador) for a in no.args))
    raise ValueError("só números, + - * / // % ** ( ), pi, e e funções como sqrt, abs, round, log")


def calcular(expressao: str) -> str:
    """Resultado da conta. Aceita ×, ÷, ^ e vírgula decimal; nada além de aritmética é executado."""
    texto = expressao.replace("×", "*").replace("÷", "/").replace("^", "**").strip()
    if not texto or len(texto) > MAX_EXPRESSAO:
        raise ValueError("expressão vazia ou longa demais")
    if "," in texto and not re.search(r"\w\s*\(", texto):
        texto = re.sub(r"(?<=\d),(?=\d)", ".", texto)
    try:
        arvore = ast.parse(texto, mode="eval")
        valor = _avaliar(arvore.body, [0])
    except (SyntaxError, ZeroDivisionError, OverflowError, TypeError) as exc:
        raise ValueError("não consegui calcular essa expressão" + (" (divisão por zero)" if isinstance(exc, ZeroDivisionError) else "")) from None
    except ValueError as exc:
        raise ValueError(str(exc)) from None
    if isinstance(valor, complex):
        raise ValueError("o resultado não é um número real")
    if isinstance(valor, float):
        if not math.isfinite(valor):
            raise ValueError("o resultado não é um número finito")
        valor = round(valor, 10)
        valor = int(valor) if valor == int(valor) and abs(valor) < 1e15 else valor
    return f"{expressao.strip()[:80]} = {valor}"


# ── unidades ─────────────────────────────────────────────────────────────
# Fator para a unidade-base de cada grandeza.
_GRANDEZAS: dict[str, dict[str, float]] = {
    "comprimento": {"mm": 0.001, "cm": 0.01, "m": 1, "km": 1000, "pol": 0.0254, "polegada": 0.0254, "pe": 0.3048, "jarda": 0.9144, "milha": 1609.344},
    "massa": {"mg": 1e-6, "g": 0.001, "kg": 1, "t": 1000, "lb": 0.45359237, "libra": 0.45359237, "oz": 0.028349523125},
    "volume": {"ml": 0.001, "l": 1, "litro": 1, "m3": 1000, "galao": 3.785411784, "xicara": 0.24},
    "tempo": {"s": 1, "min": 60, "h": 3600, "dia": 86400, "semana": 604800},
    "dados": {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4},
    "velocidade": {"m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704, "nos": 0.514444},
}
_APELIDOS = {"metro": "m", "metros": "m", "quilometro": "km", "quilometros": "km", "centimetro": "cm", "centimetros": "cm", "milimetro": "mm",
             "milimetros": "mm", "milhas": "milha", "pes": "pe", "pé": "pe", "pés": "pe", "polegadas": "pol", "in": "pol", "ft": "pe", "mi": "milha",
             "quilo": "kg", "quilos": "kg", "quilograma": "kg", "quilogramas": "kg", "grama": "g", "gramas": "g", "libras": "libra", "litros": "litro",
             "segundo": "s", "segundos": "s", "minuto": "min", "minutos": "min", "hora": "h", "horas": "h", "dias": "dia", "semanas": "semana",
             "byte": "b", "bytes": "b", "kib": "kb", "mib": "mb", "gib": "gb", "tib": "tb", "celsius": "c", "fahrenheit": "f", "kelvin": "k",
             "°c": "c", "°f": "f", "graus": "c", "galoes": "galao", "xicaras": "xicara", "nós": "nos", "noz": "nos"}


def _unidade(texto: str) -> str:
    base = texto.strip().lower().replace("º", "°")
    base = "".join(c for c in base if c.isalnum() or c in "/°")
    return _APELIDOS.get(base, base)


def _temperatura(valor: float, de: str, para: str) -> float:
    celsius = {"c": valor, "f": (valor - 32) * 5 / 9, "k": valor - 273.15}[de]
    return {"c": celsius, "f": celsius * 9 / 5 + 32, "k": celsius + 273.15}[para]


def converter(valor: float, de: str, para: str) -> str:
    """Converte entre unidades de comprimento, massa, volume, tempo, dados, velocidade e temperatura."""
    a, b = _unidade(de), _unidade(para)
    if a in "cfk" and b in "cfk" and len(a) == len(b) == 1:
        resultado = _temperatura(valor, a, b)
    else:
        for tabela in _GRANDEZAS.values():
            if a in tabela and b in tabela:
                resultado = valor * tabela[a] / tabela[b]
                break
        else:
            raise ValueError(f"não sei converter '{de[:20]}' para '{para[:20]}' (preciso da mesma grandeza)")
    return f"{valor:g} {de.strip()[:20]} = {round(resultado, 6):g} {para.strip()[:20]}"
