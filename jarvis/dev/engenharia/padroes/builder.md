nome: Builder (construtor passo a passo)
aliases: builder, construtor passo a passo, interface fluente, fluent interface, encadeamento de metodos, encadeamento de métodos, padrao builder, padrão builder
problema: Quando usar: montar um objeto complexo com muitas partes opcionais (consulta, requisição, configuração) de forma legível, em vez de um construtor com dezenas de parâmetros.
funcoes: python=demo; javascript=demo
casos: [[[], "SELECT * FROM clientes WHERE ativo = 1 AND idade > 18 LIMIT 10"]]

## Ideia
- Cada método configura UMA parte e devolve o próprio construtor, permitindo encadear chamadas.
- Um método final (`construir`) valida e produz o resultado.
- Deixa explícito o que é opcional e a ordem não importa.
- Atenção: este exemplo junta TEXTO de condições para mostrar o padrão. Com dados vindos do usuário, use parâmetros (?) em vez de concatenar, para evitar injeção de SQL.

## Pseudocódigo
```
classe ConsultaBuilder(tabela)
    onde(condicao): filtros.adicione(condicao); retorne este
    limite(n): limite ← n; retorne este
    construir(): monte o texto da consulta com os filtros e o limite
```

## Código
```python
class ConsultaBuilder:
    def __init__(self, tabela):
        self.tabela = tabela
        self._filtros = []
        self._limite = None

    def onde(self, condicao):
        self._filtros.append(condicao)
        return self

    def limite(self, quantidade):
        self._limite = quantidade
        return self

    def construir(self):
        sql = f"SELECT * FROM {self.tabela}"
        if self._filtros:
            sql += " WHERE " + " AND ".join(self._filtros)
        if self._limite is not None:
            sql += f" LIMIT {self._limite}"
        return sql


def demo():
    return ConsultaBuilder("clientes").onde("ativo = 1").onde("idade > 18").limite(10).construir()
```
```javascript
class ConsultaBuilder {
  constructor(tabela) { this.tabela = tabela; this.filtros = []; this.max = null; }
  onde(condicao) { this.filtros.push(condicao); return this; }
  limite(quantidade) { this.max = quantidade; return this; }
  construir() {
    let sql = `SELECT * FROM ${this.tabela}`;
    if (this.filtros.length) sql += " WHERE " + this.filtros.join(" AND ");
    if (this.max !== null) sql += ` LIMIT ${this.max}`;
    return sql;
  }
}

function demo() {
  return new ConsultaBuilder("clientes").onde("ativo = 1").onde("idade > 18").limite(10).construir();
}
```
