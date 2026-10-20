"""Máquina de estados PURA de um agente (sem relógio próprio, sem arquivos, sem rede).

Estados: ok | stale | error | idle | off.
- off: desligado por configuração (não é erro).
- idle: ligado, mas parado de propósito (ex.: modelo local descarregado por ociosidade).
- stale: sem batimento há mais de STALE_FATOR x a cadência, ou sem nenhum dado (ausência de dado NUNCA é ok).
- error: o último batimento foi um erro, ou um processo contínuo morreu.
"""

from __future__ import annotations

from dataclasses import dataclass

OK, STALE, ERROR, IDLE, OFF = "ok", "stale", "error", "idle", "off"
STALE_FATOR = 2.5
TOLERANCIA_OCUPADO_S = 3600.0  # uma tarefa longa em andamento não é "parada" (as tarefas têm tempo-limite menor que isso)
PRIORIDADE = {OK: 0, IDLE: 1, OFF: 2, STALE: 3, ERROR: 4}  # quanto maior, mais grave (off e idle não são problema)


@dataclass(frozen=True)
class Decisao:
    state: str
    age_s: float | None   # None = nunca houve batimento
    phase: float | None   # min(1, idade/cadência); None para contínuos ou sem dado


def decidir(agora: float, *, ligado: bool, cadencia: float | None, ultimo: float | None, ultimo_estado: str | None = None,
            vivo: bool | None = None, ocioso_legitimo: bool = False, ocupado: bool = False) -> Decisao:
    """`ultimo`/`agora` em segundos. `cadencia=None` = processo contínuo (vale `vivo`). Relógio recuado vira idade 0."""
    idade = None if ultimo is None else max(0.0, agora - ultimo)
    if not ligado:
        return Decisao(OFF, idade, None)
    if ultimo_estado == "erro":
        return Decisao(ERROR, idade, None if cadencia is None else _fase(idade, cadencia))
    if cadencia is None:
        if vivo is True:
            return Decisao(OK, idade, None)
        if vivo is False:
            return Decisao(IDLE if ocioso_legitimo else ERROR, idade, None)
        return Decisao(IDLE if ocioso_legitimo else STALE, idade, None)  # sem dado: nunca "ok"
    if idade is None:
        return Decisao(IDLE if ocioso_legitimo else STALE, None, None)
    if ocupado and idade <= TOLERANCIA_OCUPADO_S:
        return Decisao(OK, idade, _fase(idade, cadencia))
    estado = STALE if idade > STALE_FATOR * cadencia else OK
    return Decisao(estado, idade, _fase(idade, cadencia))


def _fase(idade: float | None, cadencia: float) -> float | None:
    return None if idade is None or cadencia <= 0 else min(1.0, idade / cadencia)


def resumo(estados: list[str]) -> dict:
    """{total, ok, atencao, off, pior} para o orbe. atencao = stale + error; idle conta como ok (parado de propósito)."""
    atencao = sum(1 for e in estados if e in (STALE, ERROR))
    pior = max(estados, key=lambda e: PRIORIDADE[e], default=OK)
    return {"total": len(estados), "ok": sum(1 for e in estados if e in (OK, IDLE)), "atencao": atencao,
            "off": sum(1 for e in estados if e == OFF), "pior": pior if pior in (STALE, ERROR) else OK}
