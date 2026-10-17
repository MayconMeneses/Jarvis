nome: Fila (queue)
aliases: fila, queue, fifo, enfileirar, desenfileirar, estrutura fila
problema: Guarda itens para atender na ordem de chegada: o PRIMEIRO que entrou sai primeiro (FIFO). Serve para tarefas, impressão, mensagens e busca em largura.
complexidade: enfileirar e desenfileirar: O(1) (com deque; list.pop(0) seria O(n))
funcoes: python=demo; javascript=demo
casos: [[[], ["a", "b", 2]]]

## Ideia
- Entra por um lado (fim) e sai pelo outro (começo).
- Em Python use `collections.deque` (popleft é O(1)); `list.pop(0)` é lento em filas grandes.
- Em JavaScript, `shift()` desloca todos os itens; para filas grandes use um índice de início.

## Pseudocódigo
```
enfileirar(x): coloque x no fim
desenfileirar(): se vazia, erro; senão remova e devolva o do começo
```

## Código
```python
from collections import deque


class Fila:
    def __init__(self):
        self._itens = deque()

    def enfileirar(self, item):
        self._itens.append(item)

    def desenfileirar(self):
        if not self._itens:
            raise IndexError("fila vazia")
        return self._itens.popleft()

    def espiar(self):
        return self._itens[0]

    def __len__(self):
        return len(self._itens)


def demo():
    fila = Fila()
    for letra in ("a", "b", "c"):
        fila.enfileirar(letra)
    primeiro = fila.desenfileirar()
    return [primeiro, fila.espiar(), len(fila)]
```
```javascript
class Fila {
  constructor() { this.itens = []; this.inicio = 0; }
  enfileirar(item) { this.itens.push(item); }
  desenfileirar() {
    if (this.inicio >= this.itens.length) throw new Error("fila vazia");
    return this.itens[this.inicio++];
  }
  espiar() { return this.itens[this.inicio]; }
  get tamanho() { return this.itens.length - this.inicio; }
}

function demo() {
  const fila = new Fila();
  for (const letra of ["a", "b", "c"]) fila.enfileirar(letra);
  const primeiro = fila.desenfileirar();
  return [primeiro, fila.espiar(), fila.tamanho];
}
```
