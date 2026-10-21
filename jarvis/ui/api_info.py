"""Caixas da janela principal (clima, vagas, notícias), cartão do briefing e painel de uso. SOMENTE LEITURA, sem IA.

Cada chamada devolve {ok, estado: "ok"|"vazio"|"erro", itens, atualizado_em, mensagem}. Roda na thread da ponte (a
janela não trava), guarda o resultado em memória (clima 15 min, notícias 10 min, vagas 30 min; "forcar" ignora o
cache) e, se a internet cair, devolve a última leitura boa com a hora. Título, fonte e resumo vêm de terceiros:
aqui viram texto curto sem caracteres de controle; a janela os escreve com textContent e só abre links http(s).
"""

from __future__ import annotations

import logging
import re
import threading
import time

from jarvis import config, memory_db
from jarvis.info import jobs, news, weather

log = logging.getLogger(__name__)

TTL = {"clima": 900.0, "noticias": 600.0, "vagas": 1800.0}
MAX_ITENS = 5
_CONTROLE = re.compile(r"[\x00-\x1f\x7f-\x9f​-‏‪-‮  ]+")


def _txt(valor, limite: int) -> str:
    texto = _CONTROLE.sub(" ", str(valor if valor is not None else "")).strip()
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def _link(valor) -> str:
    """Só http(s): nada de javascript:, file: etc. (a janela também confere)."""
    url = str(valor or "").strip()
    return url[:500] if url.lower().startswith(("https://", "http://")) else ""


def _agora() -> float:
    return time.time()


def _hora(ts: float) -> str:
    return time.strftime("%H:%M", time.localtime(ts))


class InfoMixin:
    """Usa self._cfg e self._memory. Métodos com "_" não viram API da janela."""

    _info_cache: dict | None = None
    _info_lock = threading.Lock()

    def _info_pegar(self, chave: str, forcar: bool, carregar) -> dict:
        """Cache + falha amigável. `carregar()` devolve (itens, mensagem_vazio) ou levanta erro."""
        with self._info_lock:
            if self._info_cache is None:
                self._info_cache = {}
            antigo = self._info_cache.get(chave)
        agora = _agora()
        if antigo and not forcar and agora - antigo["quando"] < TTL[chave]:
            return antigo["resp"]
        try:
            itens, vazio = carregar()
        except Exception:  # noqa: BLE001  (sem internet, serviço fora do ar: a caixa mostra o erro, nunca trava)
            log.debug("info: %s indisponível", chave, exc_info=True)
            if antigo:  # última leitura boa, avisando a hora
                return {**antigo["resp"], "desatualizado": True,
                        "mensagem": f"Sem internet agora. Mostrando a leitura das {_hora(antigo['quando'])}."}
            return {"ok": False, "estado": "erro", "itens": [], "atualizado_em": 0,
                    "mensagem": "Não consegui atualizar agora. Verifique a internet e tente de novo."}
        resp = {"ok": True, "estado": "ok" if itens else "vazio", "itens": itens, "atualizado_em": agora,
                "mensagem": "" if itens else vazio}
        with self._info_lock:
            self._info_cache[chave] = {"quando": agora, "resp": resp}
        return resp

    def info_clima(self, forcar: bool = False) -> dict:
        cidade = _txt(getattr(self._cfg, "city", ""), 80)
        if not cidade:
            return {"ok": True, "estado": "vazio", "itens": [], "atualizado_em": 0,
                    "mensagem": "Defina sua cidade (diga: minha cidade é ...)."}

        def carregar():
            w = weather.forecast(cidade)
            return [{"local": _txt(w["local"], 60), "agora_c": w["agora_c"], "sensacao_c": w["sensacao_c"],
                     "condicao": _txt(w["condicao"], 40), "vento_kmh": w["vento_kmh"], "maxima_c": w["maxima_c"],
                     "minima_c": w["minima_c"], "umidade": w.get("umidade_percent"),
                     "chuva": w.get("chance_chuva_percent"), "frase": _txt(weather.sentence(w), 300)}], ""

        return self._info_pegar("clima", bool(forcar), carregar)

    def info_noticias(self, forcar: bool = False) -> dict:
        def carregar():
            achado = news.headlines("gerais", limit=MAX_ITENS)
            lista = achado["manchetes"]
            if not lista and achado["avisos"]:
                raise OSError("sem manchetes")
            return [{"titulo": _txt(m["titulo"], 180), "fonte": _txt(m["fonte"], 40), "resumo": _txt(m.get("resumo"), 280),
                     "link": _link(m.get("link"))} for m in lista[:MAX_ITENS]], "Sem manchetes agora."

        return self._info_pegar("noticias", bool(forcar), carregar)

    def info_vagas(self, forcar: bool = False) -> dict:
        try:
            perfil, _ = jobs.load_profile(memory_db.open_memory(self._cfg))
        except Exception:  # noqa: BLE001
            log.debug("info: perfil de vagas ilegível", exc_info=True)
            perfil = {}
        if jobs.profile_is_empty(perfil):
            return {"ok": True, "estado": "vazio", "itens": [], "atualizado_em": 0, "pede_perfil": True,
                    "mensagem": "Preencha seu perfil de vagas para ver oportunidades."}

        def carregar():
            achado = jobs.find(perfil, limit=MAX_ITENS)
            if not achado["vagas"] and achado["avisos"]:
                raise OSError("sem vagas")
            return [{"titulo": _txt(v["titulo"], 140), "local": _txt(v["local"], 60), "fonte": _txt(v["fonte"], 40),
                     "resumo": _txt(v.get("descricao"), 280), "nota": v.get("nota"), "link": _link(v.get("link"))}
                    for v in achado["vagas"][:MAX_ITENS]], "Nenhuma vaga compatível agora."

        return self._info_pegar("vagas", bool(forcar), carregar)

    def info_briefing(self) -> dict:
        """Cartão central: compromissos de hoje, e-mails não lidos e manchetes. Texto curto, sem falar, sem gastar IA."""
        cfg = config.load()
        saida: dict = {"ok": True, "agenda": None, "emails": None, "noticias": None}
        try:
            from jarvis.agenda import servico, texto

            res = servico.do_dia(cfg)
            if not res.get("sem_agendas"):
                itens = [texto.linha(o)[2:] for o in res["ocorrencias"][:3]]
                saida["agenda"] = {"total": len(res["ocorrencias"]), "itens": [_txt(i, 90) for i in itens]}
        except Exception:  # noqa: BLE001
            log.debug("briefing: agenda indisponível", exc_info=True)
        try:
            mails = self._face_emails()
            if mails is not None:
                saida["emails"] = {"total": mails["total"], "itens": [_txt(m["assunto"], 70) for m in mails["itens"][:3]]}
        except Exception:  # noqa: BLE001
            log.debug("briefing: e-mails indisponíveis", exc_info=True)
        cache = (self._info_cache or {}).get("noticias")
        if cache:
            saida["noticias"] = {"total": len(cache["resp"]["itens"]), "itens": [i["titulo"] for i in cache["resp"]["itens"][:3]]}
        return saida

    def info_uso(self) -> dict:
        """Uso de IA de hoje para o painel lateral: tokens, custo e a barra da janela de 5 h do Claude (estimativa)."""
        from jarvis.uso import resumo, servico

        res = resumo.resumo(servico.atualizar(intervalo=5), "hoje", _agora())
        tot, j5 = res["totais"], res["cota"]["janela_5h"]
        return {"tokens": tot["tin"] + tot["tout"], "custo": tot["custo"], "estimado": tot["estimado"], "msgs": tot["msgs"],
                "pct_5h": j5.get("pct"), "alerta_5h": bool(j5.get("alerta"))}
