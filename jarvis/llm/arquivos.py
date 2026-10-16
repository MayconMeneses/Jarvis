"""Arquivos gerados pelo modelo local: validação rígida antes de escrever qualquer coisa em disco.

O modelo é uma fonte não confiável: só caminhos relativos simples, extensões de código/texto (nada executável
como .bat, .ps1 ou .exe), poucos arquivos e tamanho limitado. A escrita só ocorre numa pasta NOVA, depois que
o usuário aprova o cartão da ação.
"""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

PERMITIDAS = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".md", ".txt", ".toml", ".yml", ".yaml",
              ".sql", ".go", ".java", ".cs", ".ini", ".cfg"}
MAX_ARQUIVOS = 12
MAX_CHARS = 40_000
_NOME = re.compile(r"^[\w][\w.\-]*$")


def caminho_seguro(caminho: str) -> str:
    """Normaliza para um caminho relativo com "/" ou levanta ValueError."""
    texto = str(caminho).strip().replace("\\", "/")
    p = PurePosixPath(texto)
    if not texto or p.is_absolute() or re.match(r"^[A-Za-z]:", texto):
        raise ValueError(f"caminho não permitido: {caminho!r}")
    partes = p.parts
    if len(partes) > 4 or any(x in ("..", ".") or not _NOME.match(x) for x in partes):
        raise ValueError(f"caminho não permitido: {caminho!r}")
    if p.suffix.lower() not in PERMITIDAS:
        raise ValueError(f"tipo de arquivo não permitido: {caminho!r}")
    return "/".join(partes)


def validar(arquivos: dict[str, str]) -> dict[str, str]:
    if not arquivos:
        raise ValueError("nenhum arquivo para criar")
    if len(arquivos) > MAX_ARQUIVOS:
        raise ValueError(f"arquivos demais ({len(arquivos)}; o máximo é {MAX_ARQUIVOS})")
    limpos: dict[str, str] = {}
    for caminho, conteudo in arquivos.items():
        nome = caminho_seguro(caminho)
        if nome in limpos or not isinstance(conteudo, str) or len(conteudo) > MAX_CHARS:
            raise ValueError(f"conteúdo inválido em {caminho!r}")
        limpos[nome] = conteudo
    return limpos


def escrever(pasta: Path, arquivos: dict[str, str]) -> list[str]:
    """Grava os arquivos validados dentro de `pasta`; devolve os caminhos criados."""
    raiz = pasta.resolve()
    criados = []
    for nome, conteudo in validar(arquivos).items():
        alvo = (raiz / nome).resolve()
        if not alvo.is_relative_to(raiz):
            raise ValueError(f"caminho fora da pasta: {nome}")
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo if conteudo.endswith("\n") else conteudo + "\n", encoding="utf-8")
        criados.append(nome)
    return criados
