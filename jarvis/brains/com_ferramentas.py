"""Dá o cinto de ferramentas seguras (jarvis/llm/ferramentas_cinto.py) aos cérebros Gemini e NVIDIA.

Sem depender de MCP externo nem de function calling nativo: o laço ReAct (formato estrito, máx. 4 chamadas por pedido)
roda por cima do `ask` do cérebro. Quando o modelo responde sem pedir ferramenta, custa UMA chamada, como antes.
Ferramentas só leem; as de proposta criam cartão que o usuário aprova na janela.
"""

from __future__ import annotations

from collections.abc import Callable

from jarvis.brains.base import Answer, Brain, Message


def _somar(a: dict | None, b: dict | None) -> dict | None:
    if not a or not b:
        return a or b
    return {k: (a.get(k) or 0) + (b.get(k) or 0) for k in set(a) | set(b)}


class ComFerramentas:
    def __init__(self, cerebro: Brain, ativo: Callable[[], bool] = lambda: True) -> None:
        self._cerebro = cerebro
        self._ativo = ativo
        self.name = cerebro.name

    def __getattr__(self, nome: str):  # list_models, estado, warm_up... continuam valendo
        return getattr(self._cerebro, nome)

    def ask(self, messages: list[Message], system: str) -> Answer:
        if not self._ativo() or not messages:
            return self._cerebro.ask(messages, system)
        from jarvis.llm import ferramentas_cinto, ferramentas_laco

        cinto = ferramentas_cinto.padrao(messages[-1]["content"])
        ultima: list[Answer] = []
        uso: list[dict | None] = [None]
        custo = [0.0]

        def conversa(msgs: list[dict]) -> str:
            resposta = self._cerebro.ask(msgs[1:], msgs[0]["content"])
            ultima[:] = [resposta]
            uso[0] = _somar(uso[0], resposta.usage)
            custo[0] += resposta.custo_usd or 0.0
            return resposta.text

        resultado = ferramentas_laco.rodar(conversa, [{"role": "system", "content": system + "\n\n" + cinto.instrucao()}, *messages], cinto)
        base = ultima[0]
        return Answer(text=resultado.texto, brain=base.brain, usage=uso[0], custo_usd=custo[0] or None, modelo=base.modelo)
