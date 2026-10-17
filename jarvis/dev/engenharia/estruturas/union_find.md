nome: Union-Find (conjuntos disjuntos)
aliases: union find, union-find, conjuntos disjuntos, disjoint set, dsu, componentes conectados, agrupar elementos
problema: Agrupa elementos em conjuntos e responde, quase em O(1), se dois elementos estão no mesmo grupo e une dois grupos. Serve para redes, amizades, imagens (regiões) e o algoritmo de Kruskal.
complexidade: achar e unir: O(α(n)) amortizado, na prática constante
funcoes: python=demo; javascript=demo
casos: [[[], [true, false]]]

## Ideia
- Cada grupo tem um "representante" (a raiz). `achar(x)` sobe até a raiz.
- `unir(a, b)` liga a raiz de um grupo à raiz do outro.
- Compressão de caminho: ao achar a raiz, aponte todos os visitados direto para ela (acelera as próximas buscas).
- União por tamanho: ligue o grupo menor ao maior, para a árvore não crescer em altura.

## Pseudocódigo
```
achar(x): se pai[x] ≠ x, pai[x] ← achar(pai[x]); devolva pai[x]
unir(a, b): ra ← achar(a); rb ← achar(b); se ra ≠ rb: ligue o menor grupo ao maior
mesmo_grupo(a, b): achar(a) = achar(b)
```

## Código
```python
class UnionFind:
    def __init__(self):
        self.pai, self.tamanho = {}, {}

    def achar(self, x):
        if x not in self.pai:
            self.pai[x], self.tamanho[x] = x, 1
        if self.pai[x] != x:
            self.pai[x] = self.achar(self.pai[x])
        return self.pai[x]

    def unir(self, a, b):
        ra, rb = self.achar(a), self.achar(b)
        if ra == rb:
            return
        if self.tamanho[ra] < self.tamanho[rb]:
            ra, rb = rb, ra
        self.pai[rb] = ra
        self.tamanho[ra] += self.tamanho[rb]

    def mesmo_grupo(self, a, b):
        return self.achar(a) == self.achar(b)


def demo():
    uf = UnionFind()
    for a, b in ((1, 2), (3, 4), (2, 3)):
        uf.unir(a, b)
    return [uf.mesmo_grupo(1, 4), uf.mesmo_grupo(1, 5)]
```
```javascript
class UnionFind {
  constructor() { this.pai = new Map(); this.tamanho = new Map(); }
  achar(x) {
    if (!this.pai.has(x)) { this.pai.set(x, x); this.tamanho.set(x, 1); }
    if (this.pai.get(x) !== x) this.pai.set(x, this.achar(this.pai.get(x)));
    return this.pai.get(x);
  }
  unir(a, b) {
    let ra = this.achar(a), rb = this.achar(b);
    if (ra === rb) return;
    if (this.tamanho.get(ra) < this.tamanho.get(rb)) [ra, rb] = [rb, ra];
    this.pai.set(rb, ra);
    this.tamanho.set(ra, this.tamanho.get(ra) + this.tamanho.get(rb));
  }
  mesmoGrupo(a, b) { return this.achar(a) === this.achar(b); }
}

function demo() {
  const uf = new UnionFind();
  for (const [a, b] of [[1, 2], [3, 4], [2, 3]]) uf.unir(a, b);
  return [uf.mesmoGrupo(1, 4), uf.mesmoGrupo(1, 5)];
}
```
