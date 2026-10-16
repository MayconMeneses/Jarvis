nome: Média de uma lista
aliases: media, média, media aritmetica, média aritmética, calcular media, calcular média
problema: Calcular a média aritmética (soma dividida pela quantidade) de uma lista de números.
complexidade: tempo O(n), espaço O(1)
funcoes: python=media; javascript=media; go=media; java=media; csharp=Media
casos: [[[[1, 2, 3, 4]], 2.5], [[[10]], 10], [[[7, 8]], 7.5]]
go_teste: fmt.Println(media([]float64{1, 2, 3, 4}), media([]float64{10}), media([]float64{7, 8}))
go_saida: 2.5 10 7.5

## Ideia
- Some todos os valores com um acumulador que começa em 0.
- Divida a soma pela quantidade de elementos.
- Cuidado: lista vazia gera divisão por zero. Decida o que fazer (erro, 0 ou "sem dados").
- Em linguagens tipadas (Java, C#, Go) garanta divisão com decimais, não inteira.

## Pseudocódigo
```
função media(lista)
    se lista está vazia: erro
    soma ← 0
    para cada n em lista:
        soma ← soma + n
    retorne soma / tamanho(lista)
```

## Código
```python
def media(lista):
    if not lista:
        raise ValueError("lista vazia")
    soma = 0
    for n in lista:
        soma += n
    return soma / len(lista)
```
```javascript
function media(lista) {
  if (lista.length === 0) throw new Error("lista vazia");
  let soma = 0;
  for (const n of lista) soma += n;
  return soma / lista.length;
}
```
```go
func media(lista []float64) float64 {
	soma := 0.0
	for _, n := range lista {
		soma += n
	}
	return soma / float64(len(lista)) // a lista não pode ser vazia
}
```
```java
static double media(double[] lista) {
    if (lista.length == 0) throw new IllegalArgumentException("lista vazia");
    double soma = 0;
    for (double n : lista) soma += n;
    return soma / lista.length;
}
```
```csharp
static double Media(double[] lista)
{
    if (lista.Length == 0) throw new ArgumentException("lista vazia");
    double soma = 0;
    foreach (double n in lista) soma += n;
    return soma / lista.Length;
}
```
