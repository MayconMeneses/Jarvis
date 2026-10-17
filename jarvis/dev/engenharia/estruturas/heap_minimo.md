nome: Heap mínimo (fila de prioridade)
aliases: heap, heap minimo, heap mínimo, fila de prioridade, priority queue, min heap, monte binario, monte binário
problema: Estrutura que devolve sempre o MENOR item em O(1) e insere/remove em O(log n). É a base de filas de prioridade, do Dijkstra e do "k menores".
complexidade: espiar o menor O(1); inserir e remover O(log n)
funcoes: python=demo; javascript=demo
casos: [[[], [1, 3, 2]]]

## Ideia
- Árvore completa guardada num vetor: os filhos de i estão em 2i+1 e 2i+2; o pai de i está em (i-1)//2.
- Regra: todo pai é menor ou igual aos filhos, então o menor fica na raiz.
- Inserir: coloque no fim e "suba" trocando com o pai enquanto for menor. Remover o menor: leve o último para a raiz e "desça".
- Em Python existe o módulo `heapq`; em JavaScript não há heap nativo.

## Pseudocódigo
```
inserir(x): vetor.adicione(x); subir(ultimo indice)
remover_menor(): menor ← vetor[0]; vetor[0] ← vetor.remova_ultimo(); descer(0); devolva menor
```

## Código
```python
class HeapMinimo:
    def __init__(self):
        self._v = []

    def inserir(self, x):
        self._v.append(x)
        i = len(self._v) - 1
        while i > 0 and self._v[i] < self._v[(i - 1) // 2]:
            pai = (i - 1) // 2
            self._v[i], self._v[pai] = self._v[pai], self._v[i]
            i = pai

    def remover_menor(self):
        v = self._v
        menor, ultimo = v[0], v.pop()
        if v:
            v[0] = ultimo
            i = 0
            while True:
                esq, dir_, m = 2 * i + 1, 2 * i + 2, i
                if esq < len(v) and v[esq] < v[m]:
                    m = esq
                if dir_ < len(v) and v[dir_] < v[m]:
                    m = dir_
                if m == i:
                    break
                v[i], v[m] = v[m], v[i]
                i = m
        return menor

    def __len__(self):
        return len(self._v)


def demo():
    heap = HeapMinimo()
    for n in (5, 3, 8, 1):
        heap.inserir(n)
    return [heap.remover_menor(), heap.remover_menor(), len(heap)]
```
```javascript
class HeapMinimo {
  constructor() { this.v = []; }
  inserir(x) {
    const v = this.v;
    v.push(x);
    let i = v.length - 1;
    while (i > 0 && v[i] < v[Math.floor((i - 1) / 2)]) {
      const pai = Math.floor((i - 1) / 2);
      [v[i], v[pai]] = [v[pai], v[i]];
      i = pai;
    }
  }
  removerMenor() {
    const v = this.v, menor = v[0], ultimo = v.pop();
    if (v.length) {
      v[0] = ultimo;
      let i = 0;
      for (;;) {
        const esq = 2 * i + 1, dir = 2 * i + 2;
        let m = i;
        if (esq < v.length && v[esq] < v[m]) m = esq;
        if (dir < v.length && v[dir] < v[m]) m = dir;
        if (m === i) break;
        [v[i], v[m]] = [v[m], v[i]];
        i = m;
      }
    }
    return menor;
  }
  get tamanho() { return this.v.length; }
}

function demo() {
  const heap = new HeapMinimo();
  for (const n of [5, 3, 8, 1]) heap.inserir(n);
  return [heap.removerMenor(), heap.removerMenor(), heap.tamanho];
}
```
