"""Leitor "ler para mim": texto -> (artigo completo) -> idioma -> tradução pt-BR -> fala em partes, com parar e continuar.

Uma leitura por vez, numa thread própria. Estados: parado, baixando, traduzindo, lendo. O texto é dado de terceiros:
só é falado, nada do que ele diz vira ação.
"""

from __future__ import annotations

import logging
import re
import threading

from jarvis.info import leitor_traducao
from jarvis.info.leitor_idioma import NOMES, detectar
from jarvis.info.leitor_texto import LeituraErro, baixar_artigo

log = logging.getLogger(__name__)
PARTE_MAX = 350       # caracteres por fala: parar corta no máximo uma parte curta
RESUMO_MAX = 900
TEXTO_MAX = 6000
AVISO_ORIGINAL = "Atenção: vou ler no idioma original, a pronúncia pode sair estranha."


def partes(texto: str, limite: int = PARTE_MAX) -> list[str]:
    """Divide em partes de até `limite` caracteres, cortando em fim de frase (ou em espaço, se a frase for enorme)."""
    saida: list[str] = []
    for bloco in re.split(r"\n+", texto):
        atual = ""
        for frase in re.split(r"(?<=[.!?…])\s+", bloco.strip()):
            while len(frase) > limite:
                corte = frase.rfind(" ", 0, limite) or limite
                corte = corte if corte > 0 else limite
                if atual:
                    saida.append(atual)
                    atual = ""
                saida.append(frase[:corte].strip())
                frase = frase[corte:].strip()
            if atual and len(atual) + 1 + len(frase) > limite:
                saida.append(atual)
                atual = ""
            atual = f"{atual} {frase}".strip()
        if atual:
            saida.append(atual)
    return [p for p in saida if p]


def resumir(texto: str, limite: int = RESUMO_MAX) -> str:
    """Resumo barato e local: as primeiras frases até o limite (sem IA)."""
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    fim = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "))
    return corte[: fim + 1] if fim > limite // 3 else corte.rsplit(" ", 1)[0] + "…"


class Leitor:
    def __init__(self, cfg_fn, falar, parar_fala, baixar=baixar_artigo, traduzir=leitor_traducao.traduzir) -> None:
        self._cfg_fn = cfg_fn          # () -> Config atual
        self._falar = falar            # (texto) -> None, bloqueia até acabar ou ser parada
        self._parar_fala = parar_fala  # () -> None, corta a fala em andamento
        self._baixar = baixar
        self._traduzir = traduzir
        self._lock = threading.Lock()
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None
        self._restante: list[str] = []
        self._aviso = ""
        self._st = self._novo("parado", "")

    @staticmethod
    def _novo(estado: str, mensagem: str, **extra) -> dict:
        base = {"estado": estado, "mensagem": mensagem, "idioma": "", "parte": 0, "total": 0,
                "pode_continuar": False, "oferece_original": False}
        base.update(extra)
        return base

    def estado(self) -> dict:
        with self._lock:
            return dict(self._st)

    def _set(self, estado: str, mensagem: str = "", **extra) -> None:
        with self._lock:
            ant = self._st
            self._st = self._novo(estado, mensagem, idioma=extra.pop("idioma", ant["idioma"]),
                                  total=extra.pop("total", ant["total"]), **extra)

    def ocupado(self) -> bool:
        t = self._thread
        return t is not None and t.is_alive()

    def parar(self) -> dict:
        """Corta a fala e a preparação; o que sobrou fica para `continuar`."""
        self._parar.set()
        if self.ocupado() and self.estado()["estado"] == "lendo":  # não corta a fala de outra coisa
            self._parar_fala()
        t = self._thread
        if t is not None and t is not threading.current_thread():
            t.join(timeout=3)
        with self._lock:
            if self._st["estado"] != "parado":
                self._st = self._novo("parado", "Leitura parada.", idioma=self._st["idioma"], total=self._st["total"],
                                      parte=self._st["parte"], pode_continuar=bool(self._restante))
            return dict(self._st)

    def iniciar(self, item: dict) -> dict:
        """Começa a ler `item` (dict já validado pela ponte). Para qualquer leitura anterior primeiro."""
        self.parar()
        self._restante = []
        self._parar = threading.Event()  # um sinal por leitura: uma thread velha nunca volta a falar
        self._set("baixando" if item["completo"] and item["url"] else "traduzindo", "Preparando a leitura...")
        self._thread = threading.Thread(target=self._trabalho, args=(item, self._parar), daemon=True, name="jarvis-leitor")
        self._thread.start()
        return self.estado()

    def continuar(self) -> dict:
        with self._lock:
            sobra = list(self._restante)
        if not sobra or self.ocupado():
            return self.estado()
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._falar_partes, args=(sobra, self._parar), daemon=True, name="jarvis-leitor")
        self._thread.start()
        return self.estado()

    # ---- thread ----
    def _trabalho(self, item: dict, parar: threading.Event) -> None:
        try:
            texto = self._obter_texto(item)
            if parar.is_set():
                return
            lista = self._preparar(texto, item, parar)
            if lista is not None and not parar.is_set():
                self._falar_partes(lista, parar)
        except Exception:  # noqa: BLE001 - a janela nunca trava por causa da leitura
            log.exception("falha na leitura")
            if not parar.is_set():
                self._set("parado", "Não consegui ler isso agora.")

    def _obter_texto(self, item: dict) -> str:
        base = " ".join(x for x in (item["titulo"], item["trecho"]) if x).strip()
        self._aviso = ""
        if item["completo"] and item["url"]:
            try:
                return self._baixar(item["url"])
            except LeituraErro as exc:
                self._aviso = f"{exc} Vou ler só o resumo do cartão. "
        return base

    def _preparar(self, texto: str, item: dict, parar: threading.Event) -> list[str] | None:
        idioma = item["idioma"] if item["idioma"] in NOMES else detectar(texto)
        texto = texto[:TEXTO_MAX]
        pre: list[str] = [self._aviso.strip()] if self._aviso.strip() else []
        if idioma != "pt":
            self._set("traduzindo", f"Traduzindo do {NOMES[idioma]}...", idioma=idioma)
            try:
                texto = self._traduzir(self._cfg_fn(), texto, idioma)
            except leitor_traducao.SemCerebro:
                if parar.is_set():
                    return None
                if not item["original"]:
                    self._set("parado", f"O texto está em {NOMES[idioma]} e não há cérebro de IA disponível para traduzir. "
                              "Posso ler no idioma original com a voz em português.", idioma=idioma, oferece_original=True)
                    return None
                pre.append(AVISO_ORIGINAL)
        if item["resumir"]:
            texto = resumir(texto)
        return partes(" ".join(pre)) + partes(texto)

    def _falar_partes(self, lista: list[str], parar: threading.Event) -> None:
        total = len(lista)
        for i, parte in enumerate(lista):
            if parar.is_set():
                return
            self._set("lendo", "", parte=i + 1, total=total)
            with self._lock:
                self._restante = lista[i:]  # a parte interrompida volta a ser lida no "continuar"
            self._falar(parte)
            if parar.is_set():
                return
        if parar.is_set():
            return
        with self._lock:
            self._restante = []
        self._set("parado", "Leitura concluída.", parte=total, total=total)
