"""Cache de frases curtas e comuns já sintetizadas ("Um momento.", saudações): repetir sai na hora, sem síntese."""

from __future__ import annotations

import threading
from collections import OrderedDict

MAX_ITENS = 48
MAX_CHARS = 80  # só frases curtas: texto longo quase nunca se repete

FRASES_COMUNS = ["Um momento.", "Pois não?", "Pronto.", "Feito.", "Não entendi.", "Bom dia!", "Boa tarde!", "Boa noite!"]


class CacheFrases:
    def __init__(self, max_itens: int = MAX_ITENS) -> None:
        self._itens: OrderedDict = OrderedDict()
        self._max = max_itens
        self._trava = threading.Lock()
        self.acertos = 0
        self.erros = 0

    def pegar(self, chave: tuple):
        with self._trava:
            if chave in self._itens:
                self._itens.move_to_end(chave)
                self.acertos += 1
                return self._itens[chave]
            self.erros += 1
            return None

    def guardar(self, chave: tuple, texto: str, valor) -> None:
        if len(texto) > MAX_CHARS:
            return
        with self._trava:
            self._itens[chave] = valor
            self._itens.move_to_end(chave)
            while len(self._itens) > self._max:
                self._itens.popitem(last=False)

    def __len__(self) -> int:
        return len(self._itens)
