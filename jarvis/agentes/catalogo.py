"""Catálogo dos processos do Jarvis que o painel mostra: quem são, de quanto em quanto tempo batem e o que os liga."""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass

SEMANA_S = 7 * 86400.0
MODO_CONTINUO_ABAIXO_DE_S = 60.0  # cadência menor que isso: a tela mostra "girando", não um arco de progresso


@dataclass(frozen=True)
class Agente:
    id: str
    nome: str
    faz: str
    cadencia_s: float | None            # None = processo contínuo (vale um predicado "vivo", não um horário)
    liga: Callable[[object], bool]      # a configuração deixa este agente ligado?
    ocioso_legitimo: bool = False       # parado de propósito é normal (modelo local descarregado, semanal aguardando domingo)
    ocupado_tolera: bool = False        # uma passada longa em andamento (detalhe "executando") não é "parado"
    acao: str | None = None             # nome (da lista branca) que o botão "rodar agora" executa

    @property
    def modo(self) -> str:
        if self.cadencia_s is None:
            return "continuo"
        return "continuo" if self.cadencia_s < MODO_CONTINUO_ABAIXO_DE_S else "ciclico"


def _atualizador_ligado(cfg) -> bool:
    return bool(getattr(sys, "frozen", False) and cfg.atualizacao_automatica)  # no código-fonte fica desligado, por desenho


CATALOGO: tuple[Agente, ...] = (
    Agente("proativo", "Iniciativa própria", "Avisos sem ser chamada (bom dia, memória cheia, projetos parados)", 60.0,
           lambda c: bool(c.proativo), acao="proativo_tick"),
    Agente("autonomo", "Estudo autônomo", "Estuda sozinha o que mais conversamos, com o PC parado", 300.0, lambda c: bool(c.autonomo)),
    Agente("avaliacao_semanal", "Avaliação semanal", "Mede o cérebro local uma vez por semana (domingo)", SEMANA_S,
           lambda c: bool(c.autonomo and c.llm_local), ocioso_legitimo=True),
    Agente("sessoes", "Monitor de sessões", "Vigia as sessões do Claude Code que esperam por você", 5.0, lambda c: True, acao="sessoes_tick"),
    Agente("tarefas", "Fila de tarefas", "Executa as tarefas do Claude Code pedidas pela Jarvis", 3.0, lambda c: True, ocupado_tolera=True),
    Agente("atualizador", "Atualizador", "Procura versão nova a cada 6 horas (só na versão instalada)", 6 * 3600.0,
           _atualizador_ligado, acao="check_update"),
    Agente("celular", "Servidor do celular", "Deixa o app do celular falar com a Jarvis", None, lambda c: bool(c.celular_ativo)),
    Agente("voz", "Voz", "Escuta \"Hey Jarvis\", transcreve e fala", None, lambda c: bool(c.voz.ativa)),
    Agente("llm_local", "Cérebro local", "Modelo de IA do próprio PC (liga sob demanda, desliga parado)", None,
           lambda c: bool(c.llm_local), ocioso_legitimo=True),
)

POR_ID = {a.id: a for a in CATALOGO}
# Lista branca do botão "rodar agora" (agents_run). O estudo autônomo NÃO está aqui: pesquisa na internet e grava na memória.
ACOES_PERMITIDAS = {a.id: a.acao for a in CATALOGO if a.acao}
