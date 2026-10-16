nome: Fibonacci
aliases: fibonacci, sequencia de fibonacci, sequência de fibonacci
problema: Devolver o n-ésimo número da sequência 0, 1, 1, 2, 3, 5, 8... (cada um é a soma dos dois anteriores).
complexidade: tempo O(n), espaço O(1) (a versão recursiva ingênua é O(2ⁿ): evite)
funcoes: python=fibonacci; javascript=fibonacci; go=fibonacci; java=fibonacci; csharp=Fibonacci
casos: [[[0], 0], [[1], 1], [[2], 1], [[10], 55], [[20], 6765]]
go_teste: fmt.Println(fibonacci(0), fibonacci(1), fibonacci(2), fibonacci(10), fibonacci(20))
go_saida: 0 1 1 55 6765

## Ideia
- Guarde só os dois últimos valores (anterior e atual); não precisa de lista.
- A cada passo, o novo valor é anterior + atual, e os dois "andam" uma posição.
- Repita n vezes; no fim, "anterior" é o fibonacci(n).
- Por que não a recursão simples? fibonacci(n-1) + fibonacci(n-2) recalcula os mesmos valores milhões de vezes.

## Pseudocódigo
```
função fibonacci(n)
    anterior ← 0
    atual ← 1
    repita n vezes:
        (anterior, atual) ← (atual, anterior + atual)
    retorne anterior
```

## Código
```python
def fibonacci(n):
    anterior, atual = 0, 1
    for _ in range(n):
        anterior, atual = atual, anterior + atual
    return anterior
```
```javascript
function fibonacci(n) {
  let anterior = 0, atual = 1;
  for (let i = 0; i < n; i++) [anterior, atual] = [atual, anterior + atual];
  return anterior;
}
```
```go
func fibonacci(n int) int {
	anterior, atual := 0, 1
	for i := 0; i < n; i++ {
		anterior, atual = atual, anterior+atual
	}
	return anterior
}
```
```java
static long fibonacci(int n) {
    long anterior = 0, atual = 1;
    for (int i = 0; i < n; i++) {
        long proximo = anterior + atual;
        anterior = atual;
        atual = proximo;
    }
    return anterior;
}
```
```csharp
static long Fibonacci(int n)
{
    long anterior = 0, atual = 1;
    for (int i = 0; i < n; i++)
    {
        long proximo = anterior + atual;
        anterior = atual;
        atual = proximo;
    }
    return anterior;
}
```
