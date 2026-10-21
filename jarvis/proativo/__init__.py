"""Iniciativa própria: a Jarvis avisa sem ser chamada (bom dia, treino da semana, memória alta, projeto parado).

Cada regra é uma função pequena que olha o contexto (hora, configuração, memória, PC) e devolve um `Aviso` ou None.
Quem decide se já avisou é o agendador (uma vez por dia/semana, guardado na memória, sobrevive a reinícios).
"""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Aviso:
    chave: str        # identifica "este aviso, neste período": evita repetir
    texto: str
    falar: str = ""   # versão curta para a voz (vazio = não fala)
    voz: bool = False  # fala mesmo com a voz proativa desligada (respeita o silêncio da noite)


@dataclass
class Contexto:
    agora: datetime
    cfg: object
    ram: int = 0               # % de memória em uso agora
    ram_alta_seguidas: int = 0  # leituras seguidas acima do limite
    briefing: object = None    # função () -> {"text": ..., "speak": ...}
    treino: object = None      # função () -> str
    projetos_parados: object = None  # função () -> list[tuple[nome, dias]]
    uso: object = None         # função () -> list[(chave, texto)] (ver jarvis/uso/alertas.py)


LIMITE_RAM = 92
LEITURAS_RAM = 3
DIAS_PARADO = 14


def bom_dia(c: Contexto) -> Aviso | None:
    if not (c.cfg.proativo_hora <= c.agora.hour < 12) or c.briefing is None:
        return None
    r = c.briefing()
    return Aviso(f"bomdia:{c.agora.date()}", r["text"], r.get("speak", ""))


def treino_da_semana(c: Contexto) -> Aviso | None:
    if c.agora.weekday() != 0 or not (9 <= c.agora.hour < 20) or c.treino is None:
        return None
    ano, semana, _ = c.agora.isocalendar()
    return Aviso(f"treino:{ano}-{semana}", c.treino(), "Segunda-feira: separei o treino da semana para você.")


def memoria_alta(c: Contexto) -> Aviso | None:
    if c.ram_alta_seguidas < LEITURAS_RAM:
        return None
    # Uma vez a cada 3 horas, no máximo.
    return Aviso(f"ram:{c.agora.date()}:{c.agora.hour // 3}",
                 f"⚠️ A memória do PC está em {c.ram}% há alguns minutos. Diga \"programas pesados\" para ver o que está consumindo.",
                 "A memória do computador está quase cheia.")


def projeto_parado(c: Contexto) -> Aviso | None:
    if c.projetos_parados is None or not (9 <= c.agora.hour < 21):
        return None
    parados = c.projetos_parados()
    if not parados:
        return None
    lista = ", ".join(f"{nome} ({dias} dias)" for nome, dias in parados[:2])
    return Aviso(f"parado:{c.agora.date()}", f"💤 Sem commits há tempo: {lista}. Quer retomar? Diga \"ficha do projeto <nome>\" para eu lembrar do estado.")


def uso_de_ia(c: Contexto) -> Aviso | None:
    """Cota do Claude, orçamento ou modelo sem preço: um aviso por janela (a chave inclui o início dela)."""
    if c.uso is None:
        return None
    for chave, texto in c.uso():
        return Aviso(chave, texto)
    return None


from jarvis.proativo.evolucao import evolucao_semanal  # noqa: E402  (a regra mora em evolucao.py)
from jarvis.proativo.instagram import instagram_semanal  # noqa: E402  (a regra mora em instagram.py)

REGRAS = (bom_dia, treino_da_semana, memoria_alta, projeto_parado, uso_de_ia, instagram_semanal, evolucao_semanal)


def projetos_sem_commit(projetos: dict[str, str], dias: int = DIAS_PARADO, agora: float | None = None) -> list[tuple[str, int]]:
    """Projetos cujo último commit tem mais de `dias` dias (só leitura; ignora pasta sem git)."""
    agora = agora or time.time()
    achados = []
    for nome, pasta in projetos.items():
        if not (Path(pasta) / ".git").exists():
            continue
        try:
            saida = subprocess.run(["git", "log", "-1", "--format=%ct"], cwd=pasta, capture_output=True, text=True, timeout=5)
            idade = (agora - int(saida.stdout.strip())) / 86400
        except (OSError, ValueError, subprocess.TimeoutExpired):
            continue
        if idade > dias:
            achados.append((nome, int(idade)))
    return sorted(achados, key=lambda a: -a[1])
