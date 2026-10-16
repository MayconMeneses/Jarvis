nome: Decorator (decorador)
aliases: decorator, decorador, decorators, embrulhar funcao, embrulhar função, padrao decorator, padrão decorator
problema: Quando usar: acrescentar comportamento (log, cache, medição de tempo, verificação de permissão) a algo que já existe sem alterar o código original nem criar uma subclasse para cada combinação.
funcoes: python=demo; javascript=demo
casos: [[[], [5, ["chamando somar(2, 3)"]]]]

## Ideia
- O decorador "embrulha" o objeto ou a função original e oferece a MESMA interface.
- Antes ou depois de delegar ao original, faz o seu trabalho extra.
- Decoradores se empilham: log por fora, cache por dentro.
- Em Python existe a sintaxe @decorador; em JavaScript, funções que recebem e devolvem funções.

## Pseudocódigo
```
função comLog(funcao, registro)
    retorne função nova(args):
        registro.adicione("chamando " + nome(funcao) + args)
        retorne funcao(args)
```

## Código
```python
def com_log(funcao, registro):
    def embrulhada(*args):
        registro.append(f"chamando {funcao.__name__}{args}")
        return funcao(*args)
    return embrulhada


def somar(a, b):
    return a + b


def demo():
    registro = []
    soma = com_log(somar, registro)
    return [soma(2, 3), registro]
```
```javascript
function comLog(funcao, registro) {
  return (...args) => {
    registro.push(`chamando ${funcao.name}(${args.join(", ")})`);
    return funcao(...args);
  };
}

function somar(a, b) { return a + b; }

function demo() {
  const registro = [];
  const soma = comLog(somar, registro);
  return [soma(2, 3), registro];
}
```
