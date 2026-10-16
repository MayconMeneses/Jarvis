"""Varredura SOMENTE LEITURA de uma pasta de projeto: lista os arquivos e lê o texto do código.

Nunca escreve, apaga nem executa nada do projeto. Pastas de dependências e builds são ignoradas, o
que o .gitignore do projeto ignora também (versão simplificada), e há limites de quantidade e de tamanho
para não travar um PC fraco.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

IGNORAR = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next", "target", "bin", "obj",
           ".idea", ".vscode", ".pytest_cache", ".mypy_cache", ".cache", "site-packages", "coverage", ".tox", ".gradle"}
CODIGO = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".cs", ".php", ".rb", ".rs", ".kt", ".html", ".css", ".sql"}
MAX_ARQUIVOS = 5000
MAX_BYTES_LEITURA = 400_000
GRANDE = 5 * 1024 * 1024  # arquivo "pesado" demais para um repositório


@dataclass
class Projeto:
    raiz: Path
    arquivos: list[str] = field(default_factory=list)          # caminhos relativos (com /)
    textos: dict[str, str] = field(default_factory=dict)       # caminho -> texto (só código)
    grandes: list[str] = field(default_factory=list)
    truncado: bool = False

    def existe(self, nome: str) -> bool:
        return (self.raiz / nome).exists()


def eh_teste(caminho: str) -> bool:
    low = caminho.lower()
    nome = low.rsplit("/", 1)[-1]
    partes = low.split("/")
    return (nome.startswith("test_") or nome.endswith(("_test.py", "_test.go", ".test.js", ".test.ts", ".test.jsx", ".test.tsx",
            ".spec.js", ".spec.ts", "test.java", "tests.cs")) or any(p in ("tests", "test", "__tests__", "spec") for p in partes[:-1]))


def eh_modelo(caminho: str) -> bool:
    """Exemplos, modelos e dados que contêm valores falsos de propósito."""
    low = caminho.lower()
    return low.endswith((".tpl", ".example", ".sample")) or "/fixtures/" in low or "exemplo" in low.rsplit("/", 1)[-1]


def _padroes(pasta: Path, prefixo: str) -> list[tuple[str, str]]:
    """Linhas simples de um .gitignore: (prefixo da pasta, padrão). Ignora negações e comentários."""
    try:
        linhas = (pasta / ".gitignore").read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return [(prefixo, l.strip()) for l in linhas if l.strip() and not l.startswith(("#", "!"))]


def _ignorado(relativo: str, nome: str, padroes: list[tuple[str, str]]) -> bool:
    for prefixo, padrao in padroes:
        if prefixo and not relativo.startswith(prefixo):
            continue
        local = relativo[len(prefixo):]
        alvo = padrao.strip("/")
        if "/" in alvo:
            if fnmatch.fnmatch(local, alvo) or local.startswith(alvo + "/"):
                return True
        elif fnmatch.fnmatch(nome, alvo):
            return True
    return False


def escanear(raiz: str | Path) -> Projeto:
    base = Path(raiz).resolve()
    if not base.is_dir():
        raise ValueError(f"pasta não encontrada: {raiz}")
    projeto = Projeto(raiz=base)
    padroes = _padroes(base, "")
    for pasta, subpastas, nomes in os.walk(base):
        atual = Path(pasta)
        prefixo = "" if atual == base else atual.relative_to(base).as_posix() + "/"
        if prefixo and (atual / ".gitignore").is_file():
            padroes = padroes + _padroes(atual, prefixo)
        subpastas[:] = [d for d in subpastas if d not in IGNORAR and not _ignorado(prefixo + d, d, padroes)]
        for nome in nomes:
            relativo = prefixo + nome
            if nome != ".gitignore" and _ignorado(relativo, nome, padroes):
                continue
            if len(projeto.arquivos) >= MAX_ARQUIVOS:
                projeto.truncado = True
                return projeto
            projeto.arquivos.append(relativo)
            caminho = atual / nome
            try:
                tamanho = caminho.stat().st_size
            except OSError:
                continue
            if tamanho > GRANDE:
                projeto.grandes.append(relativo)
            elif caminho.suffix.lower() in CODIGO and tamanho <= MAX_BYTES_LEITURA:
                try:
                    projeto.textos[relativo] = caminho.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    pass
    return projeto
