"""Coletor incremental do uso do Claude Code, lendo os .jsonl que a própria ferramenta grava.

PRIVACIDADE: de cada linha só saem message.usage, message.model, message.id, requestId, timestamp,
sessionId, cwd (só o nome da pasta) e isSidechain. O texto das conversas nunca é guardado nem logado.
Só lê a pasta `projects` (nunca `sessions`, que tem chaves). Uma mensagem aparece em várias linhas
(um bloco por linha): a chave (message.id, requestId) deduplica e vale a de maior saída.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from jarvis.uso import normaliza
from jarvis.uso.registro import Registro

log = logging.getLogger(__name__)
IGNORAR = {"<synthetic>", ""}
NOVA_LINHA = bytes([10])
BLOCO = 8 * 1024 * 1024
MAX_LINHA = 64 * 1024 * 1024


def raiz_padrao() -> Path:
    if os.environ.get("JARVIS_CLAUDE_PROJECTS"):  # os testes apontam para uma pasta temporária
        return Path(os.environ["JARVIS_CLAUDE_PROJECTS"])
    return Path.home() / ".claude" / "projects"


def _epoch(texto) -> float | None:
    try:
        return datetime.fromisoformat(str(texto).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def extrair(linha: bytes, em_subagente: bool) -> dict | None:
    """Uma linha do .jsonl vira um registro, ou None se não for resposta com usage."""
    if b'"usage"' not in linha:
        return None
    try:
        evento = json.loads(linha)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None
    msg = evento.get("message") if isinstance(evento, dict) else None
    if not isinstance(msg, dict) or not isinstance(msg.get("usage"), dict):
        return None
    modelo, ts = str(msg.get("model") or ""), _epoch(evento.get("timestamp"))
    uso = normaliza.do_claude(msg["usage"])
    if modelo in IGNORAR or ts is None or not normaliza.total(uso):
        return None
    cwd = str(evento.get("cwd") or "").replace("\\", "/").rstrip("/")
    msg_id, req = msg.get("id"), evento.get("requestId")
    return {
        "ts": ts, "fonte": "jsonl", "provedor": "claude", "modelo": modelo, "projeto": cwd.rsplit("/", 1)[-1],
        "sessao": str(evento.get("sessionId") or ""), "sub": bool(evento.get("isSidechain")) or em_subagente, "uso": uso,
        "chave": f"{msg_id}|{req}" if msg_id else None,
    }


def _coletar_arquivo(reg: Registro, caminho: Path) -> int:
    """Lê só o que cresceu desde a última coleta, em blocos (um histórico de 100 MB+ não pode ir inteiro para a memória)."""
    try:
        info = caminho.stat()
    except OSError:
        return 0
    nome = str(caminho)
    posicao, _ = reg.posicao(nome)
    if info.st_size < posicao:
        posicao = 0  # o arquivo foi reescrito: relê (a chave evita duplicar)
    if info.st_size == posicao:
        return 0
    em_sub, gravadas, consumido, sobra = "subagents" in caminho.parts, 0, 0, b""
    try:
        with open(caminho, "rb") as f:
            f.seek(posicao)
            while True:
                novo = f.read(BLOCO)
                if not novo:
                    break
                bloco = sobra + novo
                fim = bloco.rfind(NOVA_LINHA) + 1  # só linhas completas; o resto fica para o próximo bloco ou a próxima coleta
                lote = [r for r in (extrair(l, em_sub) for l in bloco[:fim].splitlines()) if r]
                reg.inserir_lote(lote)
                gravadas += len(lote)
                consumido += fim
                sobra = bloco[fim:]
                if len(sobra) > MAX_LINHA:  # linha absurda sem quebra: descarta em vez de crescer sem limite
                    consumido, sobra = consumido + len(sobra), b""
    except OSError:
        log.warning("coleta de uso: leitura interrompida; segue do ponto já processado")
    reg.marcar_posicao(nome, posicao + consumido, info.st_mtime)
    return gravadas


def coletar(reg: Registro, raiz: Path | None = None) -> dict:
    """Varre a pasta e grava o que é novo. Devolve {arquivos, linhas}. Nunca levanta por arquivo ruim."""
    raiz = raiz or raiz_padrao()
    if not raiz.is_dir():
        return {"arquivos": 0, "linhas": 0}
    arquivos = linhas = 0
    for caminho in raiz.rglob("*.jsonl"):
        try:
            novas = _coletar_arquivo(reg, caminho)
        except Exception:  # um arquivo estranho não pode derrubar a coleta
            log.warning("coleta de uso: arquivo ignorado", exc_info=True)
            continue
        arquivos += 1
        linhas += novas
    return {"arquivos": arquivos, "linhas": linhas}
