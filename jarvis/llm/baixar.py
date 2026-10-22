"""Download do motor (llama.cpp) e do modelo (GGUF). Só roda depois que o usuário aprova o cartão da ação."""

from __future__ import annotations

import hashlib
import http.client
import json
import time
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from jarvis.llm import catalogo

RELEASES = "https://api.github.com/repos/ggml-org/llama.cpp/releases?per_page=8"
Progresso = Callable[[str], None]


def _abrir(url: str, timeout: int = 60, inicio: int = 0):
    cabecalhos = {"User-Agent": "SuperJarvis"}
    if inicio:
        cabecalhos["Range"] = f"bytes={inicio}-"
    return urllib.request.urlopen(urllib.request.Request(url, headers=cabecalhos), timeout=timeout)


def sha256_de(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        while bloco := f.read(1 << 20):
            h.update(bloco)
    return h.hexdigest()


def _copiar(resposta, saida, destino: Path, base: int, total: int, on_status: Progresso | None) -> None:
    feito, marco = base, base
    while bloco := resposta.read(1 << 20):
        saida.write(bloco)
        feito += len(bloco)
        if on_status and feito - marco >= 50 << 20:
            marco = feito
            on_status(f"Baixando {destino.name}: {feito >> 20} de {total >> 20 if total else '?'} MB")


def baixar_arquivo(url: str, destino: Path, on_status: Progresso | None = None, abrir=_abrir, sha256: str = "",
                   tentativas: int = 6, esperar=time.sleep) -> Path:
    """Baixa para destino.part (retoma de onde parou se a conexão cair) e só renomeia se o tamanho e,
    quando informado, o SHA-256 baterem. Arquivo pela metade ou adulterado nunca fica no lugar do bom."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(destino.name + ".part")
    total = 0
    for tentativa in range(tentativas):
        base = parcial.stat().st_size if parcial.exists() else 0
        try:
            with (abrir(url, inicio=base) if base else abrir(url)) as resposta:
                retomou = base and getattr(resposta, "status", 200) == 206
                base = base if retomou else 0
                total = base + int(resposta.headers.get("Content-Length") or 0)
                with parcial.open("ab" if retomou else "wb") as saida:
                    _copiar(resposta, saida, destino, base, total, on_status)
            break
        except (OSError, http.client.HTTPException):
            if tentativa == tentativas - 1:
                raise RuntimeError(f"a conexão caiu ao baixar {destino.name}; tente de novo (o que veio é retomado)") from None
            esperar(min(30, 2 ** tentativa))
    if total and parcial.stat().st_size != total:
        parcial.unlink(missing_ok=True)
        raise RuntimeError(f"download incompleto de {destino.name}; tente de novo")
    if sha256 and sha256_de(parcial) != sha256.lower():
        parcial.unlink(missing_ok=True)
        raise RuntimeError(f"verificação SHA-256 falhou em {destino.name}: arquivo descartado (corrompido ou adulterado)")
    parcial.replace(destino)
    return destino


def url_do_motor(abrir=_abrir) -> tuple[str, str]:
    """(nome do arquivo, url) do build Windows CPU x64 mais recente do llama.cpp."""
    with abrir(RELEASES) as resposta:
        lancamentos = json.loads(resposta.read().decode("utf-8"))
    for lancamento in lancamentos:
        for asset in lancamento.get("assets", []):
            if catalogo.MOTOR_ZIP.match(asset.get("name", "")):
                return asset["name"], asset["browser_download_url"]
    raise RuntimeError("não achei o motor do llama.cpp para Windows nas versões recentes")


def extrair(zip_path: Path, pasta: Path) -> None:
    """Extrai sem permitir caminhos que saiam da pasta (zip slip)."""
    pasta.mkdir(parents=True, exist_ok=True)
    raiz = pasta.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for nome in zf.namelist():
            if not (raiz / nome).resolve().is_relative_to(raiz):
                raise RuntimeError(f"arquivo suspeito no pacote: {nome}")
        zf.extractall(pasta)


def instalar(id_modelo: str, on_status: Progresso | None = None, abrir=_abrir) -> str:
    """Instala o que faltar (motor e modelo) em %LOCALAPPDATA%/SuperJarvis/llm. Devolve um resumo."""
    item = catalogo.modelo(id_modelo)
    dito = on_status or (lambda _: None)
    feito = []
    if catalogo.caminho_motor() is None:
        nome, url = url_do_motor(abrir)
        dito(f"Baixando o motor {nome}…")
        zip_path = baixar_arquivo(url, catalogo.raiz() / "motor" / nome, on_status, abrir)
        extrair(zip_path, catalogo.raiz() / "motor")
        zip_path.unlink(missing_ok=True)
        feito.append("motor llama.cpp")
    if catalogo.caminho_modelo(id_modelo) is None:
        dito(f"Baixando o modelo {item.nome} (cerca de {item.mb} MB)…")
        baixar_arquivo(item.url, catalogo.raiz() / "modelos" / item.arquivo, on_status, abrir, sha256=item.sha256)
        feito.append(f"modelo {item.nome}")
    return ("Instalei: " + " e ".join(feito) + ".") if feito else "O cérebro local já estava instalado."

