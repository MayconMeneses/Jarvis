"""Skill-modelo declarativa: o modelo e todas as habilidades do catálogo passam no validador."""

import json

import pytest

from jarvis.dev import habilidades
from jarvis.dev.habilidades import modelo


def test_the_model_skill_is_well_formed_and_documented():
    item = json.loads(modelo.MODELO.read_text(encoding="utf-8"))
    assert modelo.validar(item) == []
    assert set(item) == set(habilidades.catalogo()[0])  # mesmos campos das habilidades reais
    assert (modelo.MODELO.parents[4] / "docs" / "SKILLS.md").is_file()  # o passo a passo está documentado


def test_every_existing_skill_passes_the_validator():
    for item in habilidades.catalogo():
        assert modelo.validar(dict(item)) == [], item["id"]


@pytest.mark.parametrize("campo,valor", [("id", "Maiúscula Ruim"), ("nome", ""), ("medida", "sim"), ("niveis", ["só um"]), ("praticas", []), ("estudar", [""]), ("treino", " ")])
def test_malformed_skill_is_reported(campo, valor):
    item = json.loads(modelo.MODELO.read_text(encoding="utf-8"))
    item[campo] = valor
    assert modelo.validar(item)
