"""Leitura e validação do catálogo curado (catalogo.json) e montagem do comando EXATO de cada entrada."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ARQUIVO = Path(__file__).with_name("catalogo.json")
GERENCIADORES = {"npx": "Node.js (npx)", "uvx": "uv (uvx)"}
_ID = re.compile(r"^[a-z][a-z0-9_]{1,24}$")
_VERSAO = re.compile(r"^\d+(\.\d+){1,3}$")  # só versão exata: nada de ^, ~, latest ou intervalos
_PACOTE = re.compile(r"^(@[a-z0-9][a-z0-9._-]*/)?[a-z0-9][a-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SRI = re.compile(r"^sha512-[A-Za-z0-9+/]{86}==$")
_VAR_ENV = re.compile(r"^[A-Z][A-Z0-9_]{1,40}$")
CAMPOS = ("id", "nome", "gerenciador", "pacote", "versao", "integridade", "fonte", "registro", "mantenedor", "licenca", "descricao",
          "permissoes", "rede", "escreve_em_disco", "risco", "riscos", "motivo", "env", "args", "ferramentas_esperadas")


class CatalogoInvalido(ValueError):
    pass


def validar_item(item: dict) -> dict:
    """O próprio item ou CatalogoInvalido. Versão fixada, integridade presente, pacote sem caracteres estranhos."""
    faltam = [c for c in CAMPOS if c not in item]
    if faltam:
        raise CatalogoInvalido(f"entrada sem {', '.join(faltam)}")
    if not _ID.match(item["id"]) or item["gerenciador"] not in GERENCIADORES or not _PACOTE.match(item["pacote"]):
        raise CatalogoInvalido(f"entrada '{item['id']}' com id, gerenciador ou pacote inválido")
    if not _VERSAO.match(str(item["versao"])):
        raise CatalogoInvalido(f"'{item['id']}': a versão precisa ser exata (ex.: 1.2.3)")
    integridade = item["integridade"]
    if item["gerenciador"] == "npx":
        if integridade.get("tipo") != "sha512" or not _SRI.match(integridade.get("valor", "")):
            raise CatalogoInvalido(f"'{item['id']}': falta a integridade sha512 do npm")
    else:
        arquivos = integridade.get("arquivos") or {}
        if integridade.get("tipo") != "sha256" or not arquivos or not all(_SHA256.match(h) for h in arquivos.values()):
            raise CatalogoInvalido(f"'{item['id']}': faltam os hashes sha256 do PyPI")
    if item["risco"] not in ("baixo", "medio") or not item["riscos"] or not item["permissoes"]:
        raise CatalogoInvalido(f"'{item['id']}': risco, riscos e permissões são obrigatórios (risco alto não entra no catálogo)")
    if not all(isinstance(a, str) and a.startswith("--") and not re.search(r"\s", a) for a in item["args"]):
        raise CatalogoInvalido(f"'{item['id']}': argumentos extras só no formato --opcao")
    if not all(_VAR_ENV.match(k) and isinstance(v, str) for k, v in item["env"].items()):
        raise CatalogoInvalido(f"'{item['id']}': variável de ambiente inválida")
    if not str(item["fonte"]).startswith("https://github.com/") or not str(item["registro"]).startswith(("https://www.npmjs.com/", "https://pypi.org/")):
        raise CatalogoInvalido(f"'{item['id']}': fonte ou registro fora de GitHub, npm e PyPI")
    return item


@lru_cache(maxsize=1)
def _carregar() -> dict:
    dados = json.loads(ARQUIVO.read_text(encoding="utf-8"))
    ids = [validar_item(i)["id"] for i in dados["itens"]]
    if len(ids) != len(set(ids)):
        raise CatalogoInvalido("ids repetidos no catálogo")
    return dados


def itens() -> list[dict]:
    return list(_carregar()["itens"])


def recusados() -> list[dict]:
    return list(_carregar()["recusados"])


def achar(termo: str) -> dict | None:
    """A entrada pelo id, pelo nome ou por parte do nome (sem acento e sem diferenciar maiúsculas)."""
    from jarvis.dev.conhecimento import fold

    alvo = fold(termo).strip(" ?!.\"'")
    if not alvo:
        return None
    for item in itens():
        if alvo in (item["id"], fold(item["nome"]), fold(item["pacote"])):
            return item
    for item in itens():
        if alvo in fold(item["nome"]) or alvo in item["id"] or item["id"].replace("_", " ") in alvo:
            return item
    return None


def comando(item: dict, dados: str = "", executavel: str | None = None) -> tuple[str, list[str], dict[str, str]]:
    """(programa, argumentos, variáveis de ambiente) EXATOS da entrada. Nunca usa texto que não esteja no catálogo.

    npx: `npx -y pacote@versão` com scripts de instalação desligados; uvx: `uvx --no-build pacote==versão` (só binários prontos).
    No Windows, npx e uvx são scripts: `cmd /c`.
    """
    validar_item(item)
    env = {k: v.replace("{dados}", dados) for k, v in item["env"].items()}
    if item["gerenciador"] == "npx":
        argumentos = ["-y", f"{item['pacote']}@{item['versao']}", *item["args"]]
        env["npm_config_ignore_scripts"] = "true"
    else:
        argumentos = ["--no-build", f"{item['pacote']}=={item['versao']}", *item["args"]]
    programa = executavel or item["gerenciador"]
    if Path(programa).suffix.lower() in (".cmd", ".bat") or (executavel is None and __import__("sys").platform == "win32"):
        return "cmd", ["/c", programa, *argumentos], env
    return programa, argumentos, env
