"""Paridade PC x celular do casador de intenções: mesmas palavras vazias, mesmos sinônimos e o mesmo autoconhecimento."""

import json
import re
from pathlib import Path

from jarvis.local import nlp

MOVEL = Path(__file__).resolve().parent.parent / "movel"
JS = (MOVEL / "js" / "intencao-texto.js").read_text(encoding="utf-8")


def test_palavras_vazias_iguais_no_pc_e_no_celular():
    bloco = re.search(r"PALAVRAS_VAZIAS = new Set\(`(.*?)`", JS, re.S).group(1)
    assert set(bloco.split()) == set(nlp.STOPWORDS)


def test_sinonimos_iguais_no_pc_e_no_celular():
    bloco = re.search(r"export const SINONIMOS = \{(.*?)\n\};", JS, re.S).group(1)
    js = dict(re.findall(r'(\w+): "(\w+)"', bloco))
    assert js == nlp.SINONIMOS


def test_autoconhecimento_do_celular_e_o_mesmo_do_pc():
    pc = (Path(nlp.__file__).parent / "dados" / "autoconhecimento.json").read_text(encoding="utf-8")
    celular = (MOVEL / "dados" / "autoconhecimento.json").read_text(encoding="utf-8")
    assert json.loads(pc) == json.loads(celular)
