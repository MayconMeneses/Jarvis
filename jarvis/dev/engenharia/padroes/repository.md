nome: Repository (repositório)
aliases: repository, repositorio, repositório, repositorio de dados, repositório de dados, acesso a dados, padrao repository, padrão repository
problema: Quando usar: separar a regra de negócio de COMO os dados são guardados (banco, arquivo, API), para poder testar sem banco e trocar o armazenamento sem mexer nas regras.
funcoes: python=demo; javascript=demo
casos: [[[], [{"nome": "Bia", "id": 2}, 2, null]]]

## Ideia
- O repositório parece uma coleção: salvar, buscar por id, listar.
- A regra de negócio fala com a interface, nunca com SQL ou com o ORM.
- Uma versão em memória (como esta) serve para testes rápidos; a versão real usa o banco.
- Cada agregado (Pedido, Cliente) tem o seu repositório; não crie um "repositório de tudo".

## Pseudocódigo
```
interface Repositorio: salvar(item), buscar(id), listar()
classe RepositorioEmMemoria implementa Repositorio
classe RepositorioPostgres implementa Repositorio
serviço usa Repositorio (injetado)
```

## Código
```python
class RepositorioEmMemoria:
    def __init__(self):
        self._itens = {}
        self._proximo = 1

    def salvar(self, item):
        item = dict(item, id=self._proximo)
        self._itens[self._proximo] = item
        self._proximo += 1
        return item

    def buscar(self, id_item):
        return self._itens.get(id_item)

    def listar(self):
        return list(self._itens.values())


def demo():
    repo = RepositorioEmMemoria()
    repo.salvar({"nome": "Ana"})
    repo.salvar({"nome": "Bia"})
    return [repo.buscar(2), len(repo.listar()), repo.buscar(9)]
```
```javascript
class RepositorioEmMemoria {
  constructor() { this.itens = new Map(); this.proximo = 1; }
  salvar(item) {
    const salvo = { ...item, id: this.proximo };
    this.itens.set(this.proximo++, salvo);
    return salvo;
  }
  buscar(id) { return this.itens.get(id) ?? null; }
  listar() { return [...this.itens.values()]; }
}

function demo() {
  const repo = new RepositorioEmMemoria();
  repo.salvar({ nome: "Ana" });
  repo.salvar({ nome: "Bia" });
  return [repo.buscar(2), repo.listar().length, repo.buscar(9)];
}
```
