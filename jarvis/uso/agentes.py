"""Uso por sessão do Claude Code, para o Painel de Agentes.

Contrato de cada entrada: {tokens_in, tokens_out, cache, custo_usd, estimado, origem}.
- tokens_in = entrada sem cache; tokens_out = saída; cache = escrita + leitura de cache;
- custo_usd = valor equivalente em API (a assinatura não cobra por token); estimado=True quando veio da tabela de preços
  ou o modelo está sem preço (nesse caso o custo é parcial);
- origem = "jsonl" (arquivos do Claude Code), "ao_vivo" (resposta que a Jarvis mesma pediu), "misto" ou "nenhum".
Os subagentes de uma sessão são somados nela (`subagentes` traz só a parte deles).
"""

from __future__ import annotations

from jarvis.uso import servico
from jarvis.uso.registro import Registro

VAZIO = {"tokens_in": 0, "tokens_out": 0, "cache": 0, "custo_usd": 0.0, "estimado": False, "origem": "nenhum"}


def _contrato(linhas: list[dict]) -> dict:
    if not linhas:
        return dict(VAZIO)
    origens = {l["fonte"] for l in linhas}
    return {
        "tokens_in": sum(l["tin"] for l in linhas), "tokens_out": sum(l["tout"] for l in linhas),
        "cache": sum(l["cw"] + l["cr"] for l in linhas), "custo_usd": round(sum(l["custo"] for l in linhas), 4),
        "estimado": any(l["estimado"] or not l["preco_ok"] for l in linhas),
        "origem": next(iter(origens)) if len(origens) == 1 else "misto",
    }


def uso_por_sessao(session_id: str, reg: Registro | None = None) -> dict:
    """Uso de UMA sessão (inclui os subagentes dela). Sessão desconhecida devolve zeros com origem "nenhum"."""
    session_id = str(session_id or "")
    if not session_id:
        return dict(VAZIO)
    reg = reg or servico.atualizar()
    linhas = reg.linhas(sessao=session_id)
    return {**_contrato(linhas), "subagentes": _contrato([l for l in linhas if l["sub"]])}


def uso_agentes(session_ids: list[str], reg: Registro | None = None) -> dict[str, dict]:
    """Agregador único do Painel de Agentes: {session_id: contrato} numa só coleta."""
    reg = reg or servico.atualizar()
    return {str(i): uso_por_sessao(i, reg) for i in session_ids}
