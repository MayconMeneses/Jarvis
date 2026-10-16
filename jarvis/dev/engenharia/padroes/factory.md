nome: Factory (fábrica)
aliases: factory, fabrica, fábrica, factory method, fabrica de objetos, fábrica de objetos, padrao factory, padrão factory
problema: Quando usar: o tipo de objeto a criar depende de um dado (forma de pagamento, tipo de arquivo, provedor) e você quer concentrar essa decisão em UM lugar em vez de espalhar if/else.
funcoes: python=demo; javascript=demo
casos: [[[], ["pix", "cartao", "tipo desconhecido: boleto"]]]

## Ideia
- Uma função (ou classe) recebe o tipo e devolve o objeto certo; o resto do código só conhece a interface comum.
- Um dicionário de tipo → classe é a forma mais simples e fácil de estender.
- Falhe com uma mensagem clara quando o tipo não existe.
- Se só existe um tipo, não precisa de fábrica.

## Pseudocódigo
```
função criarPagamento(tipo)
    tipos ← {"pix": Pix, "cartao": Cartao}
    se tipo não está em tipos: erro "tipo desconhecido"
    retorne nova instância de tipos[tipo]
```

## Código
```python
class Pix:
    nome = "pix"


class Cartao:
    nome = "cartao"


def criar_pagamento(tipo):
    tipos = {"pix": Pix, "cartao": Cartao}
    if tipo not in tipos:
        raise ValueError(f"tipo desconhecido: {tipo}")
    return tipos[tipo]()


def demo():
    try:
        criar_pagamento("boleto")
    except ValueError as erro:
        mensagem = str(erro)
    return [criar_pagamento("pix").nome, criar_pagamento("cartao").nome, mensagem]
```
```javascript
class Pix { get nome() { return "pix"; } }
class Cartao { get nome() { return "cartao"; } }

function criarPagamento(tipo) {
  const tipos = { pix: Pix, cartao: Cartao };
  if (!(tipo in tipos)) throw new Error(`tipo desconhecido: ${tipo}`);
  return new tipos[tipo]();
}

function demo() {
  let mensagem = "";
  try { criarPagamento("boleto"); } catch (erro) { mensagem = erro.message; }
  return [criarPagamento("pix").nome, criarPagamento("cartao").nome, mensagem];
}
```
