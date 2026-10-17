nome: Pilha (stack)
aliases: pilha, stack, lifo, empilhar, desempilhar, estrutura pilha
problema: Guarda itens para tirar sempre o ÚLTIMO que entrou (LIFO). Serve para desfazer ações, voltar páginas, avaliar expressões e percorrer em profundidade.
complexidade: empilhar, desempilhar e espiar: O(1)
funcoes: python=demo; javascript=demo
casos: [[[], [3, 2, 2]]]

## Ideia
- Só se mexe numa ponta: o topo. Empilhar põe no topo; desempilhar tira do topo.
- Em Python e JavaScript, uma lista/array já serve (append/pop e push/pop), com custo O(1).
- Sempre confira se está vazia antes de desempilhar.

## Pseudocódigo
```
empilhar(x): coloque x no topo
desempilhar(): se vazia, erro; senão remova e devolva o topo
espiar(): devolva o topo sem remover
```

## Código
```python
class Pilha:
    def __init__(self):
        self._itens = []

    def empilhar(self, item):
        self._itens.append(item)

    def desempilhar(self):
        if not self._itens:
            raise IndexError("pilha vazia")
        return self._itens.pop()

    def espiar(self):
        return self._itens[-1]

    def __len__(self):
        return len(self._itens)


def demo():
    pilha = Pilha()
    for n in (1, 2, 3):
        pilha.empilhar(n)
    topo = pilha.desempilhar()
    return [topo, pilha.espiar(), len(pilha)]
```
```javascript
class Pilha {
  constructor() { this.itens = []; }
  empilhar(item) { this.itens.push(item); }
  desempilhar() {
    if (!this.itens.length) throw new Error("pilha vazia");
    return this.itens.pop();
  }
  espiar() { return this.itens[this.itens.length - 1]; }
  get tamanho() { return this.itens.length; }
}

function demo() {
  const pilha = new Pilha();
  for (const n of [1, 2, 3]) pilha.empilhar(n);
  const topo = pilha.desempilhar();
  return [topo, pilha.espiar(), pilha.tamanho];
}
```
