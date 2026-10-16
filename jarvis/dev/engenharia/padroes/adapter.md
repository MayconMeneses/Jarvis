nome: Adapter (adaptador)
aliases: adapter, adaptador, wrapper, anti corruption layer, camada anticorrupcao, camada anticorrupção, padrao adapter, padrão adapter
problema: Quando usar: você precisa usar uma API, biblioteca ou sistema legado cuja interface não combina com a do seu código; o adaptador traduz uma para a outra e isola a mudança.
funcoes: python=demo; javascript=demo
casos: [[[], {"id": 7, "nome": "Ana Silva"}]]

## Ideia
- Seu código define a interface que QUER (buscar cliente por id).
- O adaptador implementa essa interface por dentro, chamando a API externa e convertendo nomes e formatos.
- Se a API externa mudar (ou for trocada), só o adaptador muda.
- É a base de arquiteturas hexagonais (portas e adaptadores) e protege o domínio de sistemas de terceiros.

## Pseudocódigo
```
classe AdaptadorCliente(api)
    buscar(id):
        dados ← api.obterDadosDoCliente(id)
        retorne {id: dados.id_cli, nome: dados.nome_completo}
```

## Código
```python
class ApiAntiga:
    def obter_dados_do_cliente(self, id_cliente):
        return {"nome_completo": "Ana Silva", "id_cli": id_cliente}


class AdaptadorCliente:
    def __init__(self, api):
        self.api = api

    def buscar(self, id_cliente):
        dados = self.api.obter_dados_do_cliente(id_cliente)
        return {"id": dados["id_cli"], "nome": dados["nome_completo"]}


def demo():
    return AdaptadorCliente(ApiAntiga()).buscar(7)
```
```javascript
class ApiAntiga {
  obterDadosDoCliente(idCliente) { return { nome_completo: "Ana Silva", id_cli: idCliente }; }
}

class AdaptadorCliente {
  constructor(api) { this.api = api; }
  buscar(idCliente) {
    const dados = this.api.obterDadosDoCliente(idCliente);
    return { id: dados.id_cli, nome: dados.nome_completo };
  }
}

function demo() {
  return new AdaptadorCliente(new ApiAntiga()).buscar(7);
}
```
