nome: Grafo (busca em largura e em profundidade)
aliases: grafo, graph, bfs, dfs, busca em largura, busca em profundidade, lista de adjacencia, lista de adjacência, percorrer grafo
problema: Nós ligados por arestas (mapas, redes, dependências). BFS acha o caminho com menos passos; DFS explora fundo e serve para ciclos e componentes.
complexidade: BFS e DFS: O(V + A), com V nós e A arestas
funcoes: python=demo; javascript=demo
casos: [[[], [["A", "B", "C", "D"], ["A", "B", "D", "C"]]]]

## Ideia
- Guarde o grafo como lista de adjacência: para cada nó, a lista dos vizinhos.
- BFS usa uma FILA e uma lista de visitados: visita primeiro os vizinhos, depois os vizinhos dos vizinhos.
- DFS usa uma PILHA (ou recursão): segue por um caminho até o fim antes de voltar.
- Marque cada nó ao descobri-lo, para não rodar em círculo nos ciclos.

## Pseudocódigo
```
bfs(inicio): fila ← [inicio]; visto ← {inicio}
  enquanto fila: n ← tire da frente; visite n; para cada vizinho v de n: se v não visto, marque e ponha no fim da fila
dfs(n): marque n; visite n; para cada vizinho v de n: se v não visto, dfs(v)
```

## Código
```python
from collections import deque

GRAFO = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}


def bfs(grafo, inicio):
    visitados, fila, ordem = {inicio}, deque([inicio]), []
    while fila:
        no = fila.popleft()
        ordem.append(no)
        for vizinho in grafo[no]:
            if vizinho not in visitados:
                visitados.add(vizinho)
                fila.append(vizinho)
    return ordem


def dfs(grafo, no, visitados=None):
    visitados = set() if visitados is None else visitados
    visitados.add(no)
    ordem = [no]
    for vizinho in grafo[no]:
        if vizinho not in visitados:
            ordem += dfs(grafo, vizinho, visitados)
    return ordem


def demo():
    return [bfs(GRAFO, "A"), dfs(GRAFO, "A")]
```
```javascript
const GRAFO = { A: ["B", "C"], B: ["D"], C: ["D"], D: [] };

function bfs(grafo, inicio) {
  const visitados = new Set([inicio]), fila = [inicio], ordem = [];
  while (fila.length) {
    const no = fila.shift();
    ordem.push(no);
    for (const vizinho of grafo[no]) {
      if (!visitados.has(vizinho)) { visitados.add(vizinho); fila.push(vizinho); }
    }
  }
  return ordem;
}

function dfs(grafo, no, visitados = new Set()) {
  visitados.add(no);
  let ordem = [no];
  for (const vizinho of grafo[no]) {
    if (!visitados.has(vizinho)) ordem = ordem.concat(dfs(grafo, vizinho, visitados));
  }
  return ordem;
}

function demo() {
  return [bfs(GRAFO, "A"), dfs(GRAFO, "A")];
}
```
