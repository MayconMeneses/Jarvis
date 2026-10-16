nome: Busca linear
aliases: busca linear, busca sequencial, procurar em lista, buscar elemento, linear search
problema: Achar a posição de um valor numa lista (ou -1 se não existir). A lista pode estar em qualquer ordem.
complexidade: tempo O(n), espaço O(1)
funcoes: python=busca_linear; javascript=buscaLinear; go=buscaLinear; java=buscaLinear; csharp=BuscaLinear
casos: [[[[4, 8, 15], 15], 2], [[[4, 8, 15], 5], -1], [[[], 1], -1], [[[4, 8, 4], 4], 0]]
go_teste: fmt.Println(buscaLinear([]int{4, 8, 15}, 15), buscaLinear([]int{4, 8, 15}, 5), buscaLinear([]int{}, 1), buscaLinear([]int{4, 8, 4}, 4))
go_saida: 2 -1 -1 0

## Ideia
- Olhe os elementos um por um, da primeira posição até a última.
- Ao encontrar o valor, devolva a posição na hora (não precisa continuar).
- Se o laço acabar sem achar, devolva -1.
- É a única opção quando a lista NÃO está ordenada; se estiver, a busca binária é bem mais rápida.

## Pseudocódigo
```
função buscaLinear(lista, alvo)
    para i de 0 até tamanho(lista) - 1:
        se lista[i] = alvo: retorne i
    retorne -1
```

## Código
```python
def busca_linear(lista, alvo):
    for i, valor in enumerate(lista):
        if valor == alvo:
            return i
    return -1
```
```javascript
function buscaLinear(lista, alvo) {
  for (let i = 0; i < lista.length; i++) {
    if (lista[i] === alvo) return i;
  }
  return -1;
}
```
```go
func buscaLinear(lista []int, alvo int) int {
	for i, valor := range lista {
		if valor == alvo {
			return i
		}
	}
	return -1
}
```
```java
static int buscaLinear(int[] lista, int alvo) {
    for (int i = 0; i < lista.length; i++) {
        if (lista[i] == alvo) return i;
    }
    return -1;
}
```
```csharp
static int BuscaLinear(int[] lista, int alvo)
{
    for (int i = 0; i < lista.Length; i++)
    {
        if (lista[i] == alvo) return i;
    }
    return -1;
}
```
