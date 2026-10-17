nome: Trie (árvore de prefixos)
aliases: trie, arvore de prefixos, árvore de prefixos, prefix tree, autocompletar, autocomplete, busca por prefixo
problema: Árvore em que cada nível é uma letra; guarda muitas palavras e acha todas que começam com um prefixo em tempo proporcional ao tamanho do prefixo. É a base do autocompletar.
complexidade: inserir e buscar: O(m), com m = tamanho da palavra; não depende de quantas palavras existem
funcoes: python=demo; javascript=demo
casos: [[[], [["casa", "caso"], true, false]]]

## Ideia
- Cada nó tem filhos por letra e uma marca "fim de palavra" (porque "ca" pode ser prefixo de "casa" sem ser palavra).
- Para buscar por prefixo, desça até o nó do prefixo e colete todas as palavras abaixo dele.
- Gasta mais memória que uma lista de palavras, mas a busca por prefixo é muito rápida.

## Pseudocódigo
```
inserir(palavra): no ← raiz; para cada letra: no ← filho(no, letra) (crie se faltar); marque no como fim de palavra
com_prefixo(p): no ← desça pelas letras de p (se faltar, devolva vazio); colete todas as palavras abaixo de no
```

## Código
```python
class Trie:
    def __init__(self):
        self.filhos = {}
        self.fim = False

    def inserir(self, palavra):
        no = self
        for letra in palavra:
            no = no.filhos.setdefault(letra, Trie())
        no.fim = True

    def _no(self, texto):
        no = self
        for letra in texto:
            no = no.filhos.get(letra)
            if no is None:
                return None
        return no

    def contem(self, palavra):
        no = self._no(palavra)
        return bool(no and no.fim)

    def com_prefixo(self, prefixo):
        no, achadas = self._no(prefixo), []

        def coletar(atual, texto):
            if atual.fim:
                achadas.append(texto)
            for letra in sorted(atual.filhos):
                coletar(atual.filhos[letra], texto + letra)

        if no:
            coletar(no, prefixo)
        return achadas


def demo():
    trie = Trie()
    for palavra in ("casa", "caso", "cabo"):
        trie.inserir(palavra)
    return [trie.com_prefixo("cas"), trie.contem("cabo"), trie.contem("ca")]
```
```javascript
class Trie {
  constructor() { this.filhos = new Map(); this.fim = false; }
  inserir(palavra) {
    let no = this;
    for (const letra of palavra) {
      if (!no.filhos.has(letra)) no.filhos.set(letra, new Trie());
      no = no.filhos.get(letra);
    }
    no.fim = true;
  }
  _no(texto) {
    let no = this;
    for (const letra of texto) {
      no = no.filhos.get(letra);
      if (!no) return null;
    }
    return no;
  }
  contem(palavra) { const no = this._no(palavra); return Boolean(no && no.fim); }
  comPrefixo(prefixo) {
    const achadas = [];
    const coletar = (atual, texto) => {
      if (atual.fim) achadas.push(texto);
      for (const letra of [...atual.filhos.keys()].sort()) coletar(atual.filhos.get(letra), texto + letra);
    };
    const no = this._no(prefixo);
    if (no) coletar(no, prefixo);
    return achadas;
  }
}

function demo() {
  const trie = new Trie();
  for (const palavra of ["casa", "caso", "cabo"]) trie.inserir(palavra);
  return [trie.comPrefixo("cas"), trie.contem("cabo"), trie.contem("ca")];
}
```
