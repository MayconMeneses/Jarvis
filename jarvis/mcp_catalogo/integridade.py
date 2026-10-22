"""Confere, no registro oficial (npm ou PyPI), se o pacote fixado no catálogo ainda é EXATAMENTE o que foi avaliado.

O `npx` e o `uvx` não checam hash sozinhos. Aqui a Jarvis consulta o registro (endereço fixo, só leitura, tempo limitado)
e compara com o hash gravado no catálogo; se um pacote foi republicado/adulterado, a instalação é recusada.
Sem resposta do registro = não verificado = recusa (falha fechada).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

TIMEOUT = 15
MAX_BYTES = 2_000_000


@dataclass
class Verificacao:
    ok: bool
    mensagem: str


def _json(url: str, opener) -> dict:
    pedido = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SuperJarvis/1.0 (verificacao de integridade)"})
    with opener(pedido, timeout=TIMEOUT) as resp:
        return json.loads(resp.read(MAX_BYTES).decode("utf-8"))


def _npm(item: dict, opener) -> Verificacao:
    nome = urllib.parse.quote(item["pacote"], safe="@").replace("/", "%2F")
    dados = _json(f"https://registry.npmjs.org/{nome}/{item['versao']}", opener)
    atual = ((dados.get("dist") or {}).get("integrity") or "")
    if atual != item["integridade"]["valor"]:
        return Verificacao(False, "O pacote publicado no npm NÃO bate com o que foi avaliado (hash diferente). Instalação recusada.")
    if dados.get("deprecated"):
        return Verificacao(False, "O pacote foi marcado como descontinuado no npm. Instalação recusada.")
    return Verificacao(True, "Hash sha512 do npm confere com o do catálogo.")


def _pypi(item: dict, opener) -> Verificacao:
    dados = _json(f"https://pypi.org/pypi/{urllib.parse.quote(item['pacote'])}/{item['versao']}/json", opener)
    publicados = {a["filename"]: (a.get("digests") or {}).get("sha256", "") for a in dados.get("urls", [])}
    for arquivo, esperado in item["integridade"]["arquivos"].items():
        if publicados.get(arquivo) != esperado:
            return Verificacao(False, f"O arquivo {arquivo} do PyPI NÃO bate com o que foi avaliado. Instalação recusada.")
    if any(a.get("yanked") for a in dados.get("urls", [])):
        return Verificacao(False, "Esta versão foi retirada (yanked) do PyPI. Instalação recusada.")
    return Verificacao(True, "Hashes sha256 do PyPI conferem com os do catálogo.")


def verificar(item: dict, opener=urllib.request.urlopen) -> Verificacao:
    """Nunca levanta: rede fora do ar vira 'não consegui verificar' (e a instalação não segue)."""
    try:
        return (_npm if item["gerenciador"] == "npx" else _pypi)(item, opener)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return Verificacao(False, "Não consegui consultar o registro para conferir o pacote (sem internet?). Instalação recusada por segurança.")
