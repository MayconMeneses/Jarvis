"""Prepara o cérebro generativo local para ir DENTRO do instalador (funciona offline desde a 1ª abertura).

    python packaging/baixar_cerebro.py                       # motor llama.cpp + Qwen2.5 Coder 1,5B (~1,1 GB)
    python packaging/baixar_cerebro.py qwen2.5-3b            # modelo maior (~2,1 GB), mais lento
    python packaging/baixar_cerebro.py --nenhum              # remove: o instalador fica pequeno e o cérebro
                                                             # é instalado depois, por cartão aprovado

Copia para packaging/modelos/llm, de onde o Inno Setup (installer.iss) o inclui em {app}/modelos/llm.
Só use com a licença do modelo em mente (Qwen2.5 1,5B: Apache-2.0; o 3B usa a licença Qwen Research).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ALVO = ROOT / "modelos" / "llm"
sys.path.insert(0, str(ROOT.parent))


def main(argv: list[str]) -> int:
    if argv[:1] == ["--nenhum"]:
        shutil.rmtree(ALVO, ignore_errors=True)
        print("Cérebro local removido do pacote.")
        return 0
    from jarvis.llm import baixar, catalogo

    modelo = argv[0] if argv else catalogo.PADRAO
    catalogo.raiz = lambda: ALVO  # baixa direto para a pasta que o instalador inclui
    print(baixar.instalar(modelo, print))
    estado = catalogo.estado(modelo)
    if not estado["pronto"]:
        print("ERRO: a instalação ficou incompleta.")
        return 1
    total = sum(f.stat().st_size for f in ALVO.rglob("*") if f.is_file()) / 1024**2
    print(f"Pronto: {ALVO} ({total:.0f} MB). Gere o instalador em seguida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
