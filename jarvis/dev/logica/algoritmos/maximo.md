nome: Maior elemento de uma lista
aliases: maximo, máximo, maior elemento, maior valor, maior numero, maior número, max
problema: Achar o maior valor de uma lista de números (sem usar o max pronto).
complexidade: tempo O(n), espaço O(1)
funcoes: python=maximo; javascript=maximo; go=maximo; java=maximo; csharp=Maximo
casos: [[[[3, 9, 2]], 9], [[[-5, -1, -8]], -1], [[[7]], 7]]
go_teste: fmt.Println(maximo([]int{3, 9, 2}), maximo([]int{-5, -1, -8}), maximo([]int{7}))
go_saida: 9 -1 7

## Ideia
- Assuma que o primeiro elemento é o maior.
- Compare com cada um dos próximos: se achar um maior, ele passa a ser o "maior até agora".
- Não comece com 0: numa lista só de negativos a resposta estaria errada.
- Lista vazia não tem máximo: trate esse caso (erro ou valor especial).

## Pseudocódigo
```
função maximo(lista)
    se lista está vazia: erro
    maior ← lista[0]
    para cada n em lista:
        se n > maior: maior ← n
    retorne maior
```

## Código
```python
def maximo(lista):
    if not lista:
        raise ValueError("lista vazia")
    maior = lista[0]
    for n in lista:
        if n > maior:
            maior = n
    return maior
```
```javascript
function maximo(lista) {
  if (lista.length === 0) throw new Error("lista vazia");
  let maior = lista[0];
  for (const n of lista) if (n > maior) maior = n;
  return maior;
}
```
```go
func maximo(lista []int) int {
	maior := lista[0] // a lista não pode ser vazia
	for _, n := range lista {
		if n > maior {
			maior = n
		}
	}
	return maior
}
```
```java
static int maximo(int[] lista) {
    if (lista.length == 0) throw new IllegalArgumentException("lista vazia");
    int maior = lista[0];
    for (int n : lista) if (n > maior) maior = n;
    return maior;
}
```
```csharp
static int Maximo(int[] lista)
{
    if (lista.Length == 0) throw new ArgumentException("lista vazia");
    int maior = lista[0];
    foreach (int n in lista) if (n > maior) maior = n;
    return maior;
}
```
