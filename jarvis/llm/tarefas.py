"""Tarefas longas do cérebro local, em segundo plano: instalar (baixar) e criar sistemas.

Elas só PROPÕEM: instalar exige o cartão aprovado; criar termina em outro cartão com os arquivos para revisão.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from jarvis import config
from jarvis.llm import baixar, catalogo, pensar
from jarvis.llm.cerebro import conversa_local

_estado = {"instalacao": "", "criacao": ""}
_trava = threading.Lock()


def _rodar(chave: str, trabalho: Callable[[Callable[[str], None]], str]) -> bool:
    """Roda `trabalho` numa thread; False se já houver uma tarefa da mesma chave em andamento."""
    with _trava:
        if _estado[chave].startswith("⏳"):
            return False
        _estado[chave] = "⏳ começando…"

    def definir(texto: str) -> None:
        _estado[chave] = "⏳ " + texto

    def corpo() -> None:
        try:
            _estado[chave] = "✔ " + trabalho(definir)
        except Exception as exc:  # o motivo aparece no status; a Jarvis não cai
            _estado[chave] = f"✖ {exc}"

    threading.Thread(target=corpo, daemon=True).start()
    return True


def instalar(id_modelo: str, abrir=baixar._abrir) -> bool:
    def trabalho(dito):
        texto = baixar.instalar(id_modelo, dito, abrir)
        cfg = config.load()
        cfg.llm_local, cfg.llm_modelo = True, id_modelo
        config.save(cfg)
        return texto + " Cérebro local ligado."
    return _rodar("instalacao", trabalho)


def criar(nome: str, pasta_pai: str, descricao: str, store=None, conversa=None) -> bool:
    def trabalho(dito):
        from jarvis.pc import actions

        cfg = config.load()
        resultado = pensar.criar(nome, descricao, conversa or conversa_local(cfg), cfg, dito)
        actions.propose_new_project(store or actions.ActionStore(), cfg, nome, pasta_pai, descricao,
                                    "criado pelo cérebro local", arquivos=resultado.arquivos)
        aviso = (" Atenção: " + "; ".join(resultado.avisos)) if resultado.avisos else ""
        return f"Pronto: {len(resultado.arquivos)} arquivos esperam a sua aprovação no cartão.{aviso}"
    return _rodar("criacao", trabalho)


def resumo(cfg) -> str:
    est = catalogo.estado(cfg.llm_modelo, cfg.llm_endpoint)
    linhas = [f"**Cérebro local** ({est['nome']}): " + ("pronto" if est["pronto"] else f"não instalado (faltam cerca de {est['falta_mb']} MB)")
              + (", ligado" if cfg.llm_local else ", desligado")]
    for rotulo, chave in (("Instalação", "instalacao"), ("Criação de sistema", "criacao")):
        if _estado[chave]:
            linhas.append(f"- {rotulo}: {_estado[chave]}")
    return "\n".join(linhas)
