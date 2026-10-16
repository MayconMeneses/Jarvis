nome: Strategy (estratégia)
aliases: strategy, estrategia, estratégia, padrao strategy, padrão strategy
problema: Quando usar: o mesmo trabalho pode ser feito por algoritmos diferentes (calcular frete por transportadora, imposto por país, desconto por tipo de cliente) e você quer trocar de um para outro sem encher o código de if/else.
funcoes: python=demo; javascript=demo
casos: [[[], [30, 25]]]

## Ideia
- Cada algoritmo vira um objeto (ou função) com a MESMA interface.
- Quem usa (o contexto) recebe a estratégia pronta e só chama a interface; não sabe qual é.
- Para um comportamento novo, escreva uma estratégia nova: o código existente não muda (princípio aberto/fechado).
- Em linguagens com funções de primeira classe, uma função passada como argumento já é uma estratégia: não crie classes sem necessidade.

## Pseudocódigo
```
interface Frete: calcular(peso)
classe FreteCorreios implementa Frete
classe FreteTransportadora implementa Frete
classe Pedido(peso, frete): totalFrete() = frete.calcular(peso)
```

## Código
```python
class FreteCorreios:
    def calcular(self, peso):
        return 10 + peso * 2


class FreteTransportadora:
    def calcular(self, peso):
        return 15 + peso


class Pedido:
    def __init__(self, peso, frete):
        self.peso, self.frete = peso, frete

    def total_frete(self):
        return self.frete.calcular(self.peso)


def demo():
    return [Pedido(10, FreteCorreios()).total_frete(), Pedido(10, FreteTransportadora()).total_frete()]
```
```javascript
class FreteCorreios {
  calcular(peso) { return 10 + peso * 2; }
}

class FreteTransportadora {
  calcular(peso) { return 15 + peso; }
}

class Pedido {
  constructor(peso, frete) { this.peso = peso; this.frete = frete; }
  totalFrete() { return this.frete.calcular(this.peso); }
}

function demo() {
  return [new Pedido(10, new FreteCorreios()).totalFrete(), new Pedido(10, new FreteTransportadora()).totalFrete()];
}
```
