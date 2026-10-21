"""Ponte do "Ler para mim" (notícias, vagas, clima): valida o que vem da janela e entrega ao Leitor.

A resposta só traz o estado e mensagens curtas: sem chaves, sem URL, sem caminhos. O texto lido nunca vira ação.
"""

from __future__ import annotations

import logging
import threading

from jarvis import config
from jarvis.info.leitor import Leitor
from jarvis.info.leitor_texto import validar_url

log = logging.getLogger(__name__)
TIPOS = ("noticia", "vaga", "clima")
MAX_TITULO = 300
MAX_TRECHO = 6000
IDIOMAS = ("pt", "en", "es", "fr", "de", "it")


def _texto(valor: object, limite: int) -> str:
    if valor is None:
        return ""
    if not isinstance(valor, str):
        raise ValueError("texto inválido")
    return "".join(c for c in valor if c.isprintable() or c in "\n\t")[:limite].strip()


def validar_item(item: object) -> dict:
    """Item normalizado para o Leitor ou ValueError com mensagem em português (sem eco do conteúdo)."""
    if not isinstance(item, dict):
        raise ValueError("pedido de leitura inválido")
    tipo = item.get("tipo")
    if tipo not in TIPOS:
        raise ValueError("tipo de cartão desconhecido")
    titulo, trecho = _texto(item.get("titulo"), MAX_TITULO), _texto(item.get("trecho"), MAX_TRECHO)
    url = ""
    if item.get("url"):
        url = validar_url(item["url"])
    if len(titulo) + len(trecho) < 3 and not url:
        raise ValueError("não há texto para ler")
    idioma = item.get("idioma")
    if idioma is not None and idioma not in IDIOMAS:
        raise ValueError("idioma desconhecido")
    return {"tipo": tipo, "titulo": titulo, "trecho": trecho, "url": url, "idioma": idioma or "",
            "completo": bool(item.get("completo")) and bool(url), "original": bool(item.get("original")),
            "resumir": bool(item.get("resumir"))}


class LeituraMixin:
    _leitor: Leitor | None = None
    _leitor_lock = threading.Lock()

    def _falador(self):
        """(falar, parar): usa a voz da Jarvis; se a escuta está desligada, cria uma voz local só para a leitura."""
        voz = getattr(self, "_voice", None)
        if voz is not None:
            return voz.speak, voz.speaker.stop
        if getattr(self, "_speaker_leitura", None) is None:
            from jarvis.voice.tts import Speaker

            v = self._cfg.voz
            self._speaker_leitura = Speaker(v.voz, v.voz_motor, v.voz_efeito, modelo_local=v.voz_modelo, threads=v.voz_threads)
        sp = self._speaker_leitura
        return sp.say, sp.stop

    def _obter_leitor(self) -> Leitor:
        with self._leitor_lock:
            if self._leitor is None:
                self._leitor = Leitor(config.load, lambda t: self._falador()[0](t), lambda: self._falador()[1]())
            return self._leitor

    def ler_item(self, item: dict) -> dict:
        """Lê em voz alta um cartão: {tipo, titulo, trecho, url?, idioma?, completo?, original?, resumir?}. Devolve o estado."""
        try:
            limpo = validar_item(item)
        except ValueError as exc:
            return {**self._obter_leitor().estado(), "estado": "parado", "ok": False, "mensagem": str(exc)}
        try:
            return {**self._obter_leitor().iniciar(limpo), "ok": True}
        except Exception:  # noqa: BLE001
            log.exception("falha ao iniciar a leitura")
            return {"estado": "parado", "ok": False, "mensagem": "Não consegui iniciar a leitura."}

    def parar_leitura(self) -> dict:
        return {**self._obter_leitor().parar(), "ok": True}

    def continuar_leitura(self) -> dict:
        return {**self._obter_leitor().continuar(), "ok": True}

    def estado_leitura(self) -> dict:
        return {**self._obter_leitor().estado(), "ok": True}
