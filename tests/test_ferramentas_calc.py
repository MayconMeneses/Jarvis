"""Calculadora segura (AST, sem eval), conversão de unidades e data/hora por fuso."""

import pytest

from jarvis.llm import ferramentas_calc as calc


@pytest.mark.parametrize("conta,esperado", [
    ("2 + 3 * 4", "14"), ("(12.5 * 3) / 4", "9.375"), ("2 ^ 10", "1024"), ("10 ÷ 4", "2.5"), ("7 // 2", "3"), ("7 % 4", "3"),
    ("sqrt(16) + abs(-3)", "7"), ("3,5 * 2", "7"), ("-2 ** 2", "-4"), ("round(3.14159, 2)", "3.14"),
])
def test_arithmetic(conta, esperado):
    assert calc.calcular(conta).endswith(f"= {esperado}")


@pytest.mark.parametrize("ataque", [
    "__import__('os').system('calc')", "open('x')", "().__class__.__bases__", "[1,2][0]", "lambda: 1", "1 if 1 else 2", "x + 1",
    "'a' * 3", "print(1)", "eval('1')", "(1).real", "9 ** 9 ** 9", "10 ** 100000", "999999999 ** 999", "1/0", "sqrt(-1)", "(-8) ** 0.5",
    "1e400", "", "1 +", "a" * 300, "+".join(["1"] * 80),
])
def test_attacks_and_abuse_are_refused(ataque):
    with pytest.raises(ValueError):
        calc.calcular(ataque)


def test_units():
    assert calc.converter(5, "km", "milhas").endswith("3.10686 milhas")
    assert calc.converter(100, "°C", "F").endswith("= 212 F")
    assert calc.converter(1, "GB", "MB").endswith("= 1024 MB")
    assert calc.converter(90, "km/h", "m/s").endswith("= 25 m/s")
    assert calc.converter(2, "horas", "min").endswith("= 120 min")
    with pytest.raises(ValueError):
        calc.converter(1, "kg", "km")


def test_time_in_zone_and_validation():
    assert "(America/Sao_Paulo," in calc.hora_data("America/Sao_Paulo")
    assert calc.hora_data("")
    for ruim in ("../../etc", "Foo/Bar", "a b", "America/Inexistente"):
        with pytest.raises(ValueError):
            calc.hora_data(ruim)
