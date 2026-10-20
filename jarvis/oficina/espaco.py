"""Arquivos da Oficina: uma pasta por projeto em %LOCALAPPDATA%\\SuperJarvis\\oficina, com histórico de versões para desfazer.

Cada vez que um arquivo é sobrescrito ou apagado, a versão anterior vai para `.versoes/` (as últimas 20). Nada fora dessa pasta é tocado.
"""

from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from jarvis.config import data_dir
from jarvis.llm.arquivos import MAX_CHARS, caminho_seguro

MAX_ARQUIVOS = 60
MAX_VERSOES = 20
_NOME = re.compile(r"^[\w][\w \-]{0,39}$")


def raiz_padrao() -> Path:
    return data_dir() / "oficina"


class Espaco:
    def __init__(self, raiz: Path | None = None) -> None:
        self.raiz = (raiz or raiz_padrao())
        self.raiz.mkdir(parents=True, exist_ok=True)

    def _pasta(self, projeto: str) -> Path:
        if not _NOME.match(str(projeto)):
            raise ValueError("nome de projeto inválido (use letras, números, espaço e hífen; até 40 caracteres)")
        return self.raiz / projeto

    def projetos(self) -> list[str]:
        return sorted(p.name for p in self.raiz.iterdir() if p.is_dir() and not p.name.startswith("."))

    def criar(self, projeto: str) -> str:
        self._pasta(projeto).mkdir(exist_ok=True)
        return projeto

    def arquivos(self, projeto: str) -> dict[str, str]:
        pasta = self._pasta(projeto)
        achados = {}
        for p in sorted(pasta.rglob("*")) if pasta.is_dir() else []:
            relativo = p.relative_to(pasta).as_posix()
            if p.is_file() and not relativo.startswith(".versoes/") and len(achados) < MAX_ARQUIVOS:
                try:
                    achados[relativo] = p.read_text(encoding="utf-8")[:MAX_CHARS]
                except (OSError, UnicodeDecodeError):
                    continue
        return achados

    def _versoes_de(self, pasta: Path, caminho: str) -> Path:
        return pasta / ".versoes" / caminho.replace("/", "__")

    def _guardar_versao(self, pasta: Path, caminho: str, texto: str) -> None:
        destino = self._versoes_de(pasta, caminho)
        destino.mkdir(parents=True, exist_ok=True)
        # O relógio do Windows é grosso (duas gravações seguidas teriam o mesmo nome e uma versão sumiria): o nome só cresce.
        ultimo = max((int(v.stem) for v in destino.glob("*.txt") if v.stem.isdigit()), default=0)
        (destino / f"{max(time.time_ns(), ultimo + 1)}.txt").write_text(texto, encoding="utf-8")
        for velha in sorted(destino.glob("*.txt"))[:-MAX_VERSOES]:
            velha.unlink(missing_ok=True)

    def salvar(self, projeto: str, caminho: str, conteudo: str) -> str:
        pasta, nome = self._pasta(projeto), caminho_seguro(caminho)
        if len(conteudo) > MAX_CHARS:
            raise ValueError(f"arquivo grande demais (máximo {MAX_CHARS} caracteres)")
        alvo = pasta / nome
        if not alvo.exists() and len(self.arquivos(projeto)) >= MAX_ARQUIVOS:
            raise ValueError(f"projeto com arquivos demais (máximo {MAX_ARQUIVOS})")
        alvo.parent.mkdir(parents=True, exist_ok=True)
        if alvo.is_file():
            antigo = alvo.read_text(encoding="utf-8")
            if antigo == conteudo:
                return nome
            self._guardar_versao(pasta, nome, antigo)
        alvo.write_text(conteudo, encoding="utf-8")
        return nome

    def apagar(self, projeto: str, caminho: str) -> bool:
        pasta, nome = self._pasta(projeto), caminho_seguro(caminho)
        alvo = pasta / nome
        if not alvo.is_file():
            return False
        self._guardar_versao(pasta, nome, alvo.read_text(encoding="utf-8"))
        alvo.unlink()
        return True

    def versoes(self, projeto: str, caminho: str) -> int:
        return len(list(self._versoes_de(self._pasta(projeto), caminho_seguro(caminho)).glob("*.txt")))

    def desfazer(self, projeto: str, caminho: str) -> str:
        """Volta o arquivo para a versão anterior (a atual vira uma versão, então dá para refazer desfazendo de novo)."""
        pasta, nome = self._pasta(projeto), caminho_seguro(caminho)
        pasta_versoes = self._versoes_de(pasta, nome)
        anteriores = sorted(pasta_versoes.glob("*.txt")) if pasta_versoes.is_dir() else []
        if not anteriores:
            raise ValueError("não há versão anterior deste arquivo")
        ultima = anteriores[-1]
        texto = ultima.read_text(encoding="utf-8")
        alvo = pasta / nome
        if alvo.is_file():
            self._guardar_versao(pasta, nome, alvo.read_text(encoding="utf-8"))
        ultima.unlink()
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(texto, encoding="utf-8")
        return texto

    def excluir_projeto(self, projeto: str) -> None:
        shutil.rmtree(self._pasta(projeto), ignore_errors=True)
