nome: Tabela hash (hash map)
aliases: tabela hash, hash map, hashmap, tabela de dispersao, tabela de dispersão, dicionario, dicionário, hash table, mapa chave valor
problema: Guarda pares chave→valor e acha o valor pela chave em tempo médio O(1), transformando a chave num número (hash) que escolhe uma "gaveta".
complexidade: inserir, buscar e remover: O(1) em média; O(n) no pior caso (muitas colisões)
funcoes: python=demo; javascript=demo
casos: [[[], [3, null, 2]]]

## Ideia
- Uma função de hash converte a chave em um índice de um vetor de "gavetas".
- Colisão (duas chaves na mesma gaveta) é normal: cada gaveta guarda uma pequena lista (encadeamento).
- Quando as gavetas enchem demais, dobra-se o tamanho e reespalham-se os itens (aqui omitido para ficar curto).
- Em Python o `dict` e em JavaScript o `Map` já fazem isso otimizado: use-os; implementar serve para entender.

## Pseudocódigo
```
colocar(chave, valor): g ← gaveta[hash(chave) mod n]; se chave está em g, troque o valor; senão, acrescente (chave, valor)
pegar(chave): procure a chave na gaveta[hash(chave) mod n]; devolva o valor ou nada
```

## Código
```python
class TabelaHash:
    def __init__(self, gavetas=8):
        self._gavetas = [[] for _ in range(gavetas)]
        self._tamanho = 0

    def _gaveta(self, chave):
        return self._gavetas[hash(chave) % len(self._gavetas)]

    def colocar(self, chave, valor):
        gaveta = self._gaveta(chave)
        for i, (k, _) in enumerate(gaveta):
            if k == chave:
                gaveta[i] = (chave, valor)
                return
        gaveta.append((chave, valor))
        self._tamanho += 1

    def pegar(self, chave, padrao=None):
        for k, v in self._gaveta(chave):
            if k == chave:
                return v
        return padrao

    def __len__(self):
        return self._tamanho


def demo():
    tabela = TabelaHash()
    tabela.colocar("a", 1)
    tabela.colocar("b", 2)
    tabela.colocar("a", 3)
    return [tabela.pegar("a"), tabela.pegar("z"), len(tabela)]
```
```javascript
class TabelaHash {
  constructor(gavetas = 8) { this.gavetas = Array.from({ length: gavetas }, () => []); this.tamanho = 0; }
  hash(chave) {
    let h = 0;
    for (const c of String(chave)) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    return h % this.gavetas.length;
  }
  colocar(chave, valor) {
    const gaveta = this.gavetas[this.hash(chave)];
    const par = gaveta.find(([k]) => k === chave);
    if (par) { par[1] = valor; return; }
    gaveta.push([chave, valor]);
    this.tamanho++;
  }
  pegar(chave, padrao = null) {
    const par = this.gavetas[this.hash(chave)].find(([k]) => k === chave);
    return par ? par[1] : padrao;
  }
}

function demo() {
  const tabela = new TabelaHash();
  tabela.colocar("a", 1);
  tabela.colocar("b", 2);
  tabela.colocar("a", 3);
  return [tabela.pegar("a"), tabela.pegar("z"), tabela.tamanho];
}
```
