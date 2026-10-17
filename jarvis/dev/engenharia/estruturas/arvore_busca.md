nome: Árvore binária de busca (BST)
aliases: arvore binaria de busca, árvore binária de busca, arvore de busca, árvore de busca, bst, binary search tree, arvore binaria, árvore binária
problema: Árvore onde, em cada nó, os menores ficam à esquerda e os maiores à direita; inserir e buscar custam O(log n) quando ela está equilibrada, e a leitura em ordem sai ordenada.
complexidade: buscar e inserir: O(log n) equilibrada, O(n) se degenerar em lista; percorrer em ordem: O(n)
funcoes: python=demo; javascript=demo
casos: [[[], [[1, 3, 4, 5, 8], true, false]]]

## Ideia
- Compare o valor com o nó: menor vai para a esquerda, maior para a direita, até achar um lugar vazio (inserir) ou o valor (buscar).
- Ler esquerda → nó → direita (em ordem) devolve os valores ordenados.
- Inserir valores já ordenados degenera a árvore numa lista; árvores balanceadas (AVL, rubro-negra) evitam isso.

## Pseudocódigo
```
inserir(no, x): se no é vazio, crie nó(x); se x < no.valor, no.esq ← inserir(no.esq, x); senão se x > no.valor, no.dir ← inserir(no.dir, x)
em_ordem(no): se no: em_ordem(no.esq); visite no; em_ordem(no.dir)
```

## Código
```python
class No:
    def __init__(self, valor):
        self.valor, self.esq, self.dir = valor, None, None


class Arvore:
    def __init__(self):
        self.raiz = None

    def inserir(self, valor):
        self.raiz = self._inserir(self.raiz, valor)

    def _inserir(self, no, valor):
        if no is None:
            return No(valor)
        if valor < no.valor:
            no.esq = self._inserir(no.esq, valor)
        elif valor > no.valor:
            no.dir = self._inserir(no.dir, valor)
        return no

    def contem(self, valor):
        no = self.raiz
        while no:
            if valor == no.valor:
                return True
            no = no.esq if valor < no.valor else no.dir
        return False

    def em_ordem(self):
        saida = []

        def visitar(no):
            if no:
                visitar(no.esq)
                saida.append(no.valor)
                visitar(no.dir)

        visitar(self.raiz)
        return saida


def demo():
    arvore = Arvore()
    for n in (5, 3, 8, 1, 4):
        arvore.inserir(n)
    return [arvore.em_ordem(), arvore.contem(4), arvore.contem(7)]
```
```javascript
class No {
  constructor(valor) { this.valor = valor; this.esq = null; this.dir = null; }
}

class Arvore {
  constructor() { this.raiz = null; }
  inserir(valor) { this.raiz = this._inserir(this.raiz, valor); }
  _inserir(no, valor) {
    if (!no) return new No(valor);
    if (valor < no.valor) no.esq = this._inserir(no.esq, valor);
    else if (valor > no.valor) no.dir = this._inserir(no.dir, valor);
    return no;
  }
  contem(valor) {
    let no = this.raiz;
    while (no) {
      if (valor === no.valor) return true;
      no = valor < no.valor ? no.esq : no.dir;
    }
    return false;
  }
  emOrdem() {
    const saida = [];
    const visitar = (no) => { if (no) { visitar(no.esq); saida.push(no.valor); visitar(no.dir); } };
    visitar(this.raiz);
    return saida;
  }
}

function demo() {
  const arvore = new Arvore();
  for (const n of [5, 3, 8, 1, 4]) arvore.inserir(n);
  return [arvore.emOrdem(), arvore.contem(4), arvore.contem(7)];
}
```
