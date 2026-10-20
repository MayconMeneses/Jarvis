"""Painel de agentes na ponte da janela: agents_status (só leitura) e agents_run (lista branca, clique explícito)."""

from __future__ import annotations

import logging
import time

from jarvis import config
from jarvis.agentes import painel, uso_adaptador
from jarvis.agentes.catalogo import ACOES_PERMITIDAS, POR_ID
from jarvis.agentes.registro import registro

log = logging.getLogger(__name__)


class AgentsMixin:
    """Usa self._voice, self._mobile (definidos em Api/MobileMixin). Métodos com "_" não viram API da janela."""

    _acoes_agentes: dict | None = None
    _leitor_sessoes = None
    _provedor_uso = None

    def _registrar_acao(self, nome: str, funcao) -> None:
        """Quem monta a janela entrega o que o botão "rodar agora" pode chamar. Só nomes da lista branca valem."""
        if nome in ACOES_PERMITIDAS.values():
            self._acoes_agentes = {**(self._acoes_agentes or {}), nome: funcao}

    def _vivos(self) -> dict:
        voz = getattr(self, "_voice", None)
        mobile = getattr(self, "_mobile", None)
        return {"voz": bool(voz is not None and voz.is_alive()), "celular": bool(mobile and mobile.ativo)}

    def _subagentes(self) -> list:
        from jarvis.dev.sessions import SessionReader

        if self._leitor_sessoes is None:
            self._leitor_sessoes = SessionReader()
        return self._leitor_sessoes.subagentes()

    def agents_status(self) -> dict:
        """Retrato dos agentes. GET idempotente: não executa nada, não usa rede nem IA e não devolve segredos."""
        resposta = painel.retrato(config.load(), vivos=self._vivos())
        resposta["subagentes"] = painel.subagentes_do_claude(self._subagentes)
        resposta["uso"] = uso_adaptador.uso_atual(self._provedor_uso)
        return resposta

    def agents_run(self, agente_id: str) -> dict:
        """"Rodar agora": só ações da lista branca, e só por clique do usuário. O estudo autônomo nunca está nela."""
        nome = ACOES_PERMITIDAS.get(str(agente_id))
        if nome is None:
            return {"ok": False, "mensagem": "Este agente não tem ação manual."}
        funcao = {"check_update": getattr(self, "check_update", None), **(self._acoes_agentes or {})}.get(nome)
        if funcao is None:
            return {"ok": False, "mensagem": "Essa ação não está disponível agora."}
        antes = registro.ler(agente_id)
        try:
            funcao()
        except Exception as exc:  # noqa: BLE001
            log.exception("falha ao rodar %s", nome)
            return {"ok": False, "mensagem": f"Não deu certo ({type(exc).__name__}). Detalhes no log.", "ts_antes": antes.ts if antes else None}
        depois = registro.ler(agente_id)
        return {"ok": True, "mensagem": f"{POR_ID[agente_id].nome}: rodou agora.", "ts_antes": antes.ts if antes else None,
                "ts_depois": depois.ts if depois else time.time()}
