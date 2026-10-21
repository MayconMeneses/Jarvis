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


def modelos_texto() -> str:
    """Projetos prontos (as mesmas peças do PC) com marcadores __NOME__/__SLUG__/__DESCRICAO__ para o celular preencher."""
    from jarvis.dev import modelos

    combinacoes = ["fastapi", "express", "react", "html", "fastapi+react", "fastapi+html", "express+react", "express+html"]
    saida = {}
    for c in combinacoes:  # nomes-sentinela: o slug sai "xnomex" e vira __SLUG__ (o celular preenche tudo na criação)
        arquivos = modelos.arquivos(c, "XNOMEX", "XDESCX")
        saida[c] = {"descricao": modelos.descricao(c), "arquivos": {
            k: v.replace("XNOMEX", "__NOME__").replace("xnomex", "__SLUG__").replace("XDESCX", "__DESCRICAO__") for k, v in arquivos.items()}}
    return json.dumps(saida, ensure_ascii=False, separators=(",", ":")) + "\n"


def texto() -> str:
    return json.dumps(montar(), ensure_ascii=False, separators=(",", ":")) + "\n"


def autoconhecimento_texto() -> str:
    """Cópia do autoconhecimento do PC (jarvis/local/dados/autoconhecimento.json), byte a byte: uma fonte só."""
    from jarvis.local import autoconhecimento

    return autoconhecimento.ARQUIVO.read_text(encoding="utf-8")


def main(argv: list[str]) -> int:
    destino = RAIZ / "dados" / "saber.json"
    auto = RAIZ / "dados" / "autoconhecimento.json"
    if "--conferir" in argv:
        modelos = RAIZ / "dados" / "modelos.json"
        return 0 if (destino.is_file() and destino.read_text(encoding="utf-8") == texto()
                     and modelos.is_file() and modelos.read_text(encoding="utf-8") == modelos_texto()
                     and auto.is_file() and auto.read_text(encoding="utf-8") == autoconhecimento_texto()) else 1
    from jarvis.mobile import icones

    destino.parent.mkdir(exist_ok=True)
    destino.write_text(texto(), encoding="utf-8")
    (RAIZ / "dados" / "modelos.json").write_text(modelos_texto(), encoding="utf-8")
    auto.write_text(autoconhecimento_texto(), encoding="utf-8")
    (RAIZ / "icones").mkdir(exist_ok=True)
    for tamanho in (180, 192, 512):  # só regrava o que mudou (não suja o Git à toa)
        alvo, novo = RAIZ / "icones" / f"icone-{tamanho}.png", icones.png(tamanho)
        if not alvo.is_file() or alvo.read_bytes() != novo:
            alvo.write_bytes(novo)
    print(f"Gravado {destino} ({destino.stat().st_size // 1024} KB) e os ícones.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
