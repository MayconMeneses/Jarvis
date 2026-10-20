"""Tela FACE: dados reais dos painéis laterais. SOMENTE LEITURA, só contagens e texto curto.

Um único face_dados(): cada bloco roda isolado (falhou = None, e a janela mostra "—").
Assunto e remetente de e-mail são dado de terceiros: aqui só viram texto truncado e sem controle;
a janela os escreve com textContent. E-mail marcado como suspeito nem chega à tela.
"""

from __future__ import annotations

import logging
import re
import time

from jarvis import config, mail
from jarvis.agentes import painel
from jarvis.dev import runs_store

log = logging.getLogger(__name__)

MAX_ITENS = 5
CACHE_EMAIL_S = 60.0
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2028\u2029]+")


def _relogio() -> float:
    return time.monotonic()


def _txt(valor, limite: int) -> str:
    texto = _CONTROLE.sub(" ", str(valor if valor is not None else "")).strip()
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


class FaceMixin:
    """Usa self._cfg, self._window e self._leitor_sessoes (AgentsMixin). Métodos com "_" não viram API da janela."""

    _face_cache_mail: tuple[float, dict | None] | None = None
    _face_cheia = False

    def face_dados(self) -> dict:
        blocos = {"vitals": self._face_vitals, "sessoes": self._face_sessoes, "emails": self._face_emails,
                  "tarefas": self._face_tarefas, "status": self._face_status, "logs": self._face_logs}
        dados: dict = {}
        for nome, funcao in blocos.items():
            try:
                dados[nome] = funcao()
            except Exception:  # noqa: BLE001  (um painel quebrado não derruba os outros)
                log.debug("FACE: bloco %s indisponível", nome, exc_info=True)
                dados[nome] = None
        return dados

    def _face_vitals(self) -> dict:
        import psutil

        return {"cpu": round(psutil.cpu_percent(interval=0.1)), "ram": round(psutil.virtual_memory().percent)}

    def _face_sessoes(self) -> dict:
        from jarvis.dev import sessions, sessions_model as modelo

        if self._leitor_sessoes is None:
            self._leitor_sessoes = sessions.SessionReader()
        achadas = self._leitor_sessoes.sessions()
        contagem = {e: 0 for e in (modelo.PERMISSAO, modelo.PERGUNTA, modelo.AGUARDANDO, modelo.TRABALHANDO)}
        for s in achadas:
            if s.estado in contagem:
                contagem[s.estado] += 1
        ordem = {e: i for i, e in enumerate(contagem)}
        visiveis = sorted((s for s in achadas if s.estado in contagem), key=lambda s: ordem[s.estado])
        return {"contagem": contagem, "total": len(achadas),
                "itens": [{"projeto": _txt(s.projeto, 24), "estado": s.estado} for s in visiveis[:MAX_ITENS]]}

    def _face_emails(self) -> dict | None:
        agora = _relogio()
        if self._face_cache_mail is not None and agora - self._face_cache_mail[0] < CACHE_EMAIL_S:
            return self._face_cache_mail[1]
        try:
            achado = mail.recent(self._cfg, limit=20, unread_only=True)
            mails = achado.get("emails") or []
            if not mails and achado.get("avisos"):
                valor = None  # sem conta ou com erro: "—", não "0"
            else:
                seguros = [m for m in mails if m.get("categoria_por_regra") != "Suspeito" and not m.get("alerta")]
                valor = {"total": len(seguros), "mais": len(mails) >= 20,
                         "itens": [{"de": _txt(m.get("remetente"), 32), "assunto": _txt(m.get("assunto"), 60)}
                                   for m in seguros[:MAX_ITENS]]}
        except Exception:  # noqa: BLE001
            log.debug("FACE: e-mails indisponíveis", exc_info=True)
            valor = None
        self._face_cache_mail = (agora, valor)  # falha também espera 60 s: não martela o provedor
        return valor

    def _face_tarefas(self) -> dict:
        todas = runs_store.RunStore().all()
        return {"rodando": sum(1 for r in todas if r.status == "rodando"), "fila": sum(1 for r in todas if r.status == "na_fila"),
                "itens": [{"projeto": _txt(r.projeto, 24), "status": _txt(r.status, 16), "tarefa": _txt(r.tarefa, 60)}
                          for r in list(reversed(todas))[:4]]}

    def _retrato_agentes(self) -> dict:
        return painel.retrato(self._cfg, vivos=self._vivos())

    def _face_status(self) -> dict:
        r = self._retrato_agentes()["resumo"]
        return {k: r.get(k) for k in ("total", "ok", "atencao", "off", "pior")}

    def _face_logs(self) -> list:
        itens = [a for a in self._retrato_agentes()["agentes"] if a.get("last_ts")]
        itens.sort(key=lambda a: a["last_ts"], reverse=True)
        return [{"ts": a["last_ts"], "agente": _txt(a["nome"], 28), "estado": _txt(a["state"], 12),
                 "detalhe": _txt(a.get("detalhe"), 60)} for a in itens[:MAX_ITENS]]

    def face_ao_abrir(self) -> bool:
        return bool(getattr(self._cfg, "face_ao_abrir", False))

    def definir_face_ao_abrir(self, valor) -> bool:
        self._cfg.face_ao_abrir = valor is True
        config.save(self._cfg)
        return self._cfg.face_ao_abrir

    def face_tela_cheia(self) -> bool:
        """Alterna a tela cheia do monitor (opcional). False se a janela não conseguir."""
        try:
            self._window.toggle_fullscreen()
        except Exception:  # noqa: BLE001
            log.debug("FACE: tela cheia indisponível", exc_info=True)
            return False
        self._face_cheia = not self._face_cheia
        return self._face_cheia
