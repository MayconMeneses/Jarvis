nome: Observer (observador)
aliases: observer, observador, pub sub, publicar e assinar, eventos e ouvintes, listener, listeners, padrao observer, padrão observer
problema: Quando usar: vários interessados precisam ser avisados quando algo acontece (pedido criado: enviar e-mail, registrar log, atualizar estoque) sem que quem avisa conheça cada um deles.
funcoes: python=demo; javascript=demo
casos: [[[], [["email", "pedido 1"], ["log", "pedido 1"]]]]

## Ideia
- Quem produz o evento mantém uma lista de ouvintes (funções ou objetos) e os chama quando algo acontece.
- Ouvintes se inscrevem e podem sair; o produtor não depende deles.
- Cuidado: um ouvinte lento ou com erro não pode derrubar os outros (trate erros por ouvinte).
- Em sistemas maiores, o mesmo ideia vira mensageria (filas e tópicos).

## Pseudocódigo
```
classe Evento
    ouvintes ← lista vazia
    inscrever(f): adicione f em ouvintes
    emitir(dado): para cada f em ouvintes: f(dado)
```

## Código
```python
class Evento:
    def __init__(self):
        self._ouvintes = []

    def inscrever(self, funcao):
        self._ouvintes.append(funcao)

    def emitir(self, dado):
        for funcao in self._ouvintes:
            funcao(dado)


def demo():
    recebidos = []
    evento = Evento()
    evento.inscrever(lambda d: recebidos.append(["email", d]))
    evento.inscrever(lambda d: recebidos.append(["log", d]))
    evento.emitir("pedido 1")
    return recebidos
```
```javascript
class Evento {
  constructor() { this.ouvintes = []; }
  inscrever(funcao) { this.ouvintes.push(funcao); }
  emitir(dado) { for (const funcao of this.ouvintes) funcao(dado); }
}

function demo() {
  const recebidos = [];
  const evento = new Evento();
  evento.inscrever((d) => recebidos.push(["email", d]));
  evento.inscrever((d) => recebidos.push(["log", d]));
  evento.emitir("pedido 1");
  return recebidos;
}
```
