"""Agendamento do Radar DENTRO do app (sem tarefa do Windows, sem serviço): confere a cada 5 minutos.

Roda no dia útil, a partir da hora escolhida e uma vez por dia (a marca fica na memória, então rodar na mão também conta).
Se a Jarvis estava fechada na hora, roda na próxima vez que abrir e avisa "boletim atrasado".
Falhou 2 dias seguidos? O próximo boletim começa com um aviso. O áudio nunca toca sozinho.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timedelta

from jarvis.radar import executar, ia_resumo
from jarvis.radar.historico import Historico

log = logging.getLogger(__name__)
ATRASO_MAX = timedelta(hours=1)  # depois disso conta como "boletim atrasado"
REPETIR_FALHA = timedelta(minutes=30)


def hora_de(texto: str) -> tuple[int, int]:
    try:
        h, m = (int(p) for p in str(texto).strip().split(":"))
        return (h, m) if 0 <= h < 24 and 0 <= m < 60 else (7, 0)
    except ValueError:
        return 7, 0


class RadarAgendador:
    def __init__(self, cfg_loader, mem, entregar: Callable[[str], None], rodar=executar.executar,
                 historico=Historico, agora: Callable[[], datetime] = datetime.now) -> None:
        self._cfg_loader, self._mem, self._entregar = cfg_loader, mem, entregar
        self._rodar, self._historico, self._agora = rodar, historico, agora
        self._trava = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def devido(self, cfg, agora: datetime) -> tuple[bool, bool]:
        """(deve rodar agora, é atrasado). Regras: ligado, com nicho, dia útil, depois da hora, uma vez por dia."""
        r = cfg.radar
        if not r.ativo or not r.nicho.strip() or (r.dias_uteis and agora.weekday() >= 5):
            return False, False
        h, m = hora_de(r.hora)
        alvo = agora.replace(hour=h, minute=m, second=0, microsecond=0)
        dia = agora.strftime("%Y-%m-%d")
        if agora < alvo or self._mem.meta(f"radar:{dia}"):
            return False, False
        ultima = self._mem.meta("radar:tentativa")
        if ultima and agora - datetime.fromisoformat(ultima) < REPETIR_FALHA and ultima.startswith(dia):
            return False, False  # falhou há pouco (sem internet?): tenta de novo só depois do prazo
        return True, agora - alvo > ATRASO_MAX

    def _seguidas(self) -> int:
        return int(self._mem.meta("radar:falhas_seguidas") or 0)

    def executar(self, progresso=None, atrasado: bool = False, sem_audio: bool = False) -> dict:
        """Uma execução (agendada ou manual). Nunca roda duas ao mesmo tempo."""
        if not self._trava.acquire(blocking=False):
            return {"ok": False, "erro": "O Radar já está rodando; aguarde terminar."}
        try:
            cfg, agora = self._cfg_loader(), self._agora()
            avisos = ["O Radar falhou nos últimos dias; confira as fontes e a internet."] if self._seguidas() >= 2 else []
            hist = self._historico()
            try:
                ajustes = replace(cfg.radar, audio=False) if sem_audio else cfg.radar
                resultado = self._rodar(ajustes, hist, self._mem, agora, progresso=progresso, atrasado=atrasado, avisos_iniciais=avisos,
                                       melhorar=ia_resumo.criar(cfg))
            finally:
                hist.fechar()
            self._registrar(resultado, agora)
            return resultado
        finally:
            self._trava.release()

    def _registrar(self, resultado: dict, agora: datetime) -> None:
        dia = agora.strftime("%Y-%m-%d")
        if resultado["ok"]:
            self._mem.set_meta("radar:falhas_seguidas", "0")
            minutos = round(resultado["duracao_s"] / 60, 1)
            audio = f", {minutos:g} min de áudio" if resultado.get("audio") else ""
            self._entregar(f"📰 Radar pronto: {resultado['itens']} notícias{audio}. Diga \"abrir radar\"" + (" ou \"ouvir radar\"." if resultado.get("audio") else "."))
            return
        self._mem.set_meta("radar:tentativa", agora.isoformat(timespec="seconds"))
        if self._mem.meta("radar:falha_dia") != dia:  # conta no máximo uma falha por dia
            self._mem.set_meta("radar:falha_dia", dia)
            self._mem.set_meta("radar:falhas_seguidas", str(self._seguidas() + 1))

    def tick(self) -> dict | None:
        cfg, agora = self._cfg_loader(), self._agora()
        deve, atrasado = self.devido(cfg, agora)
        return self.executar(atrasado=atrasado) if deve else None

    def start(self, intervalo: float = 300.0) -> None:
        def laco() -> None:
            while True:
                try:
                    self.tick()
                except Exception:
                    log.warning("radar: falha no agendador", exc_info=True)
                if self._parar.wait(intervalo):
                    return

        self._thread = threading.Thread(target=laco, daemon=True, name="jarvis-radar")
        self._thread.start()

    def stop(self) -> None:
        self._parar.set()
