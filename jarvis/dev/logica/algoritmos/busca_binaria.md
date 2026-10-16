nome: Busca binária
aliases: busca binaria, busca binária, binary search, pesquisa binaria, pesquisa binária
problema: Achar um valor numa lista JÁ ORDENADA, descartando metade dos candidatos a cada passo. Devolve a posição ou -1.
complexidade: tempo O(log n), espaço O(1)
funcoes: python=busca_binaria; javascript=buscaBinaria; go=buscaBinaria; java=buscaBinaria; csharp=BuscaBinaria
casos: [[[[1, 3, 5, 7, 9, 11], 7], 3], [[[1, 3, 5, 7, 9, 11], 1], 0], [[[1, 3, 5, 7, 9, 11], 11], 5], [[[1, 3, 5, 7, 9, 11], 4], -1], [[[], 1], -1]]
go_teste: fmt.Println(buscaBinaria([]int{1, 3, 5, 7, 9, 11}, 7), buscaBinaria([]int{1, 3, 5, 7, 9, 11}, 1), buscaBinaria([]int{1, 3, 5, 7, 9, 11}, 11), buscaBinaria([]int{1, 3, 5, 7, 9, 11}, 4), buscaBinaria([]int{}, 1))
go_saida: 3 0 5 -1 -1

## Ideia
- Pré-requisito: a lista precisa estar ordenada.
- Mantenha dois limites: esquerda e direita (começam nas pontas).
- Olhe o elemento do meio: se for o alvo, achou; se o alvo for maior, descarte a metade da esquerda; se for menor, descarte a da direita.
- Repita até os limites se cruzarem: o valor não existe (-1).
- Cada passo corta o problema pela metade: 1 milhão de itens exige só ~20 comparações.

## Pseudocódigo
```
função buscaBinaria(lista, alvo)
    esq ← 0
    dir ← tamanho(lista) - 1
    enquanto esq ≤ dir:
        meio ← (esq + dir) ÷ 2
        se lista[meio] = alvo: retorne meio
        se lista[meio] < alvo: esq ← meio + 1
        senão: dir ← meio - 1
    retorne -1
```

## Código
```python
def busca_binaria(lista, alvo):
    esq, dir = 0, len(lista) - 1
    while esq <= dir:
        meio = (esq + dir) // 2
        if lista[meio] == alvo:
            return meio
        if lista[meio] < alvo:
            esq = meio + 1
        else:
            dir = meio - 1
    return -1
```
```javascript
function buscaBinaria(lista, alvo) {
  let esq = 0, dir = lista.length - 1;
  while (esq <= dir) {
    const meio = Math.floor((esq + dir) / 2);
    if (lista[meio] === alvo) return meio;
    if (lista[meio] < alvo) esq = meio + 1;
    else dir = meio - 1;
  }
  return -1;
}
```
```go
func buscaBinaria(lista []int, alvo int) int {
	esq, dir := 0, len(lista)-1
	for esq <= dir {
		meio := (esq + dir) / 2
		if lista[meio] == alvo {
			return meio
		}
		if lista[meio] < alvo {
			esq = meio + 1
		} else {
			dir = meio - 1
		}
	}
	return -1
}
```
```java
static int buscaBinaria(int[] lista, int alvo) {
    int esq = 0, dir = lista.length - 1;
    while (esq <= dir) {
        int meio = esq + (dir - esq) / 2;
        if (lista[meio] == alvo) return meio;
        if (lista[meio] < alvo) esq = meio + 1;
        else dir = meio - 1;
    }
    return -1;
}
```
```csharp
static int BuscaBinaria(int[] lista, int alvo)
{
    int esq = 0, dir = lista.Length - 1;
    while (esq <= dir)
    {
        int meio = esq + (dir - esq) / 2;
        if (lista[meio] == alvo) return meio;
        if (lista[meio] < alvo) esq = meio + 1;
        else dir = meio - 1;
    }
    return -1;
}
```
