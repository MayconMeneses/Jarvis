nome: Lista ligada (linked list)
aliases: lista ligada, lista encadeada, linked list, lista simplesmente encadeada, nos encadeados
problema: Itens ligados por referências (cada nó aponta para o próximo). Inserir no começo é O(1) e não precisa de espaço contíguo; buscar por posição é O(n).
complexidade: inserir no início O(1); inserir no fim O(n) sem ponteiro de cauda; buscar O(n)
funcoes: python=demo; javascript=demo
casos: [[[], [[0, 1, 2, 3], [3, 2, 1, 0]]]]

## Ideia
- Cada nó guarda um valor e a referência do próximo; o último aponta para nada (None/null).
- Para inverter, vá religando cada nó ao anterior enquanto caminha.
- Na prática, listas/arrays nativos costumam ser melhores; a lista ligada ensina ponteiros e aparece em entrevistas.

## Pseudocódigo
```
inserir_no_inicio(x): novo ← nó(x, proximo=cabeca); cabeca ← novo
inverter(): anterior ← nada; atual ← cabeca
  enquanto atual: prox ← atual.proximo; atual.proximo ← anterior; anterior ← atual; atual ← prox
  cabeca ← anterior
```

## Código
```python
class No:
    def __init__(self, valor, proximo=None):
        self.valor, self.proximo = valor, proximo


class ListaLigada:
    def __init__(self):
        self.cabeca = None

    def inserir_no_inicio(self, valor):
        self.cabeca = No(valor, self.cabeca)

    def adicionar(self, valor):
        if self.cabeca is None:
            self.cabeca = No(valor)
            return
        atual = self.cabeca
        while atual.proximo:
            atual = atual.proximo
        atual.proximo = No(valor)

    def inverter(self):
        anterior, atual = None, self.cabeca
        while atual:
            atual.proximo, anterior, atual = anterior, atual, atual.proximo
        self.cabeca = anterior

    def para_lista(self):
        itens, atual = [], self.cabeca
        while atual:
            itens.append(atual.valor)
            atual = atual.proximo
        return itens


def demo():
    lista = ListaLigada()
    for n in (1, 2, 3):
        lista.adicionar(n)
    lista.inserir_no_inicio(0)
    antes = lista.para_lista()
    lista.inverter()
    return [antes, lista.para_lista()]
```
```javascript
class No {
  constructor(valor, proximo = null) { this.valor = valor; this.proximo = proximo; }
}

class ListaLigada {
  constructor() { this.cabeca = null; }
  inserirNoInicio(valor) { this.cabeca = new No(valor, this.cabeca); }
  adicionar(valor) {
    if (!this.cabeca) { this.cabeca = new No(valor); return; }
    let atual = this.cabeca;
    while (atual.proximo) atual = atual.proximo;
    atual.proximo = new No(valor);
  }
  inverter() {
    let anterior = null, atual = this.cabeca;
    while (atual) {
      const proximo = atual.proximo;
      atual.proximo = anterior;
      anterior = atual;
      atual = proximo;
    }
    this.cabeca = anterior;
  }
  paraLista() {
    const itens = [];
    for (let atual = this.cabeca; atual; atual = atual.proximo) itens.push(atual.valor);
    return itens;
  }
}

function demo() {
  const lista = new ListaLigada();
  for (const n of [1, 2, 3]) lista.adicionar(n);
  lista.inserirNoInicio(0);
  const antes = lista.paraLista();
  lista.inverter();
  return [antes, lista.paraLista()];
}
```
