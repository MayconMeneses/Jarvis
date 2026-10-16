"""Prepara o modelo de voz que vai DENTRO do instalador (funciona offline desde a 1ª abertura).

    python packaging/baixar_modelo.py            # small (padrão da Jarvis, ~465 MB)
    python packaging/baixar_modelo.py base       # menor (~145 MB), mais erros de transcrição
    python packaging/baixar_modelo.py --nenhum   # remove o modelo: o instalador fica pequeno e o
                                                 # modelo é baixado na 1ª abertura

Copia para packaging/modelos/whisper-<tamanho>, de onde o Inno Setup (installer.iss) o inclui em
{app}\\modelos. Se o modelo já estiver no cache do Hugging Face deste PC, nada é baixado.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "modelos"


def main(argv: list[str]) -> int:
    if argv[:1] == ["--nenhum"]:
        shutil.rmtree(TARGET, ignore_errors=True)
        print("Modelo removido do pacote; o instalador baixará na primeira abertura.")
        return 0
    size = argv[0] if argv else "small"
    from faster_whisper.utils import download_model

    try:
        source = Path(download_model(size, local_files_only=True))
        print(f"Usando o modelo que já está no cache deste PC: {source}")
    except Exception:  # noqa: BLE001
        print(f"Baixando o modelo {size}...")
        source = Path(download_model(size, output_dir=str(Path(tempfile.mkdtemp(prefix="jarvis-modelo-")) / size)))
    folder = TARGET / f"whisper-{size}"
    shutil.rmtree(TARGET, ignore_errors=True)  # só um tamanho por instalador
    folder.mkdir(parents=True)
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, folder / item.name)
    missing = [n for n in ("model.bin", "config.json") if not (folder / n).is_file()]
    if missing:
        print(f"ERRO: faltam arquivos do modelo: {missing}")
        return 1
    total = sum(f.stat().st_size for f in folder.iterdir()) / 1024**2
    print(f"Pronto: {folder} ({total:.0f} MB). Gere o instalador em seguida.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
