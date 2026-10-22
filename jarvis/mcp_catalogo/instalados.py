"""O que está instalado (aprovado) e a configuração do Claude CLI gerada SÓ a partir disso.

O arquivo `mcp_instalados.json` guarda apenas ids do catálogo, versão, data e ferramentas vistas no teste. O comando que
roda é recalculado do catálogo a cada geração: texto digitado ou gravado aqui nunca vira comando. Se a versão registrada
deixou de ser a do catálogo (o catálogo foi atualizado), o servidor sai da configuração até o usuário aprovar de novo.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jarvis.config import data_dir
from jarvis.mcp_catalogo import catalogo

PREFIXO = "ext_"
MAX_HISTORICO = 100


def arquivo() -> Path:
    return data_dir() / "mcp_instalados.json"


def ler(alvo: Path | None = None) -> dict:
    try:
        dados = json.loads((alvo or arquivo()).read_text(encoding="utf-8"))
        itens = [i for i in dados.get("itens", []) if isinstance(i, dict) and isinstance(i.get("id"), str)]
        return {"itens": itens, "historico": [h for h in dados.get("historico", []) if isinstance(h, dict)]}
    except (OSError, ValueError, AttributeError):
        return {"itens": [], "historico": []}


def _gravar(dados: dict, alvo: Path | None = None) -> None:
    destino = alvo or arquivo()
    destino.parent.mkdir(parents=True, exist_ok=True)
    dados["historico"] = dados["historico"][-MAX_HISTORICO:]
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def registrar(item: dict, ferramentas: list[str], alvo: Path | None = None) -> None:
    dados = ler(alvo)
    dados["itens"] = [i for i in dados["itens"] if i["id"] != item["id"]]
    dados["itens"].append({"id": item["id"], "versao": item["versao"], "pacote": item["pacote"], "instalado_em": _agora(),
                           "ativo": True, "ferramentas": ferramentas[:30]})
    dados["historico"].append({"quando": _agora(), "acao": "instalou", "id": item["id"], "versao": item["versao"]})
    _gravar(dados, alvo)


def remover(id_: str, desativar: bool = False, alvo: Path | None = None) -> bool:
    """True se havia o que remover/desativar."""
    dados = ler(alvo)
    achado = next((i for i in dados["itens"] if i["id"] == id_), None)
    if achado is None:
        return False
    if desativar:
        achado["ativo"] = False
    else:
        dados["itens"].remove(achado)
    dados["historico"].append({"quando": _agora(), "acao": "desativou" if desativar else "removeu", "id": id_, "versao": achado.get("versao", "")})
    _gravar(dados, alvo)
    return True


def registro_de(id_: str, alvo: Path | None = None) -> dict | None:
    return next((i for i in ler(alvo)["itens"] if i["id"] == id_), None)


def ativos(alvo: Path | None = None) -> list[tuple[dict, dict]]:
    """[(entrada do catálogo, registro)] dos aprovados, ativos e ainda na versão fixada do catálogo."""
    por_id = {i["id"]: i for i in catalogo.itens()}
    return [(por_id[r["id"]], r) for r in ler(alvo)["itens"]
            if r.get("ativo") and r["id"] in por_id and r.get("versao") == por_id[r["id"]]["versao"]]


def servidores(alvo: Path | None = None, dados: str | None = None) -> dict[str, dict]:
    """Bloco `mcpServers` dos aprovados (chave ext_<id>). Vazio se não há nenhum."""
    pasta = dados if dados is not None else str(data_dir())
    saida = {}
    for item, _ in ativos(alvo):
        programa, argumentos, env = catalogo.comando(item, pasta)
        bloco = {"command": programa, "args": argumentos}
        if env:
            bloco["env"] = env
        saida[PREFIXO + item["id"]] = bloco
    return saida


def permitidas(caminho_config: Path | None) -> list[str]:
    """Nomes `mcp__ext_<id>` liberados no --allowedTools, lidos do próprio mcp.json (só o que está nele)."""
    if caminho_config is None:
        return []
    try:
        chaves = json.loads(Path(caminho_config).read_text(encoding="utf-8"))["mcpServers"]
    except (OSError, ValueError, KeyError, TypeError):
        return []
    return [f"mcp__{k}" for k in chaves if isinstance(k, str) and k.startswith(PREFIXO)]


def resumo(alvo: Path | None = None) -> str:
    dados = ler(alvo)
    if not dados["itens"]:
        return "Nenhuma ferramenta externa instalada."
    linhas = []
    for r in dados["itens"]:
        item = next((i for i in catalogo.itens() if i["id"] == r["id"]), None)
        estado = "ativa" if r.get("ativo") and item and item["versao"] == r.get("versao") else "desativada ou desatualizada"
        linhas.append(f"- {item['nome'] if item else r['id']} {r.get('versao', '')} ({estado}), instalada em {str(r.get('instalado_em', ''))[:10]}")
    return "\n".join(linhas)
