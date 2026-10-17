"""Gera movel/dados/saber.json e os ícones a partir da base curada do PC (uma fonte só: jarvis/dev).

    python movel/gerar_dados.py          # grava
    python movel/gerar_dados.py --conferir   # só confere se está em dia (usado nos testes)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ.parent))

TOPICO = ("id", "nome", "aliases", "resumo", "passos", "analogia", "exemplo", "erros", "exercicios")
TECNOLOGIA = ("id", "nome", "categoria", "areas", "aliases", "resumo", "usos", "fortes", "fracos", "quando", "curva", "comeco")
ALGORITMO = ("id", "nome", "aliases", "problema", "complexidade", "ideia", "pseudocodigo", "codigo")
PADRAO = ("id", "nome", "aliases", "problema", "ideia", "pseudocodigo", "codigo")
HABILIDADE = ("id", "nome", "medida", "resumo", "niveis", "praticas", "estudar", "treino")


def _campos(item: dict, nomes: tuple[str, ...]) -> dict:
    return {n: item[n] for n in nomes if n in item}


def montar() -> dict:
    from jarvis.dev import conhecimento, engenharia, habilidades, logica, ux

    topicos = ([{**_campos(i, TOPICO), "area": "logica"} for i in logica.conceitos()]
               + [{**_campos(i, TOPICO), "area": "engenharia"} for i in engenharia.itens()]
               + [{**_campos(i, TOPICO), "area": "ux"} for i in ux.itens()])
    return {
        "topicos": topicos,
        "tecnologias": [_campos(i, TECNOLOGIA) for i in conhecimento.entries()],
        "algoritmos": [_campos(i, ALGORITMO) for i in logica.algoritmos()],
        "padroes": [_campos(i, PADRAO) for i in engenharia.padroes()],
        "estruturas": [_campos(i, (*PADRAO, "complexidade")) for i in engenharia.estruturas()],
        "tipos": list(conhecimento.system_types()),
        "habilidades": [_campos(i, HABILIDADE) for i in habilidades.catalogo()],
    }


def texto() -> str:
    return json.dumps(montar(), ensure_ascii=False, separators=(",", ":")) + "\n"


def main(argv: list[str]) -> int:
    destino = RAIZ / "dados" / "saber.json"
    if "--conferir" in argv:
        return 0 if destino.is_file() and destino.read_text(encoding="utf-8") == texto() else 1
    from jarvis.mobile import icones

    destino.parent.mkdir(exist_ok=True)
    destino.write_text(texto(), encoding="utf-8")
    (RAIZ / "icones").mkdir(exist_ok=True)
    for tamanho in (180, 192, 512):
        (RAIZ / "icones" / f"icone-{tamanho}.png").write_bytes(icones.png(tamanho))
    print(f"Gravado {destino} ({destino.stat().st_size // 1024} KB) e os ícones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
