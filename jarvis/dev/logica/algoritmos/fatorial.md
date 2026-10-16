nome: Fatorial
aliases: fatorial, n!, factorial
problema: Calcular n! = n × (n-1) × ... × 2 × 1, com 0! = 1.
complexidade: tempo O(n), espaço O(1)
funcoes: python=fatorial; javascript=fatorial; go=fatorial; java=fatorial; csharp=Fatorial
casos: [[[5], 120], [[0], 1], [[1], 1], [[10], 3628800]]
go_teste: fmt.Println(fatorial(5), fatorial(0), fatorial(1), fatorial(10))
go_saida: 120 1 1 3628800

## Ideia
- Comece com resultado = 1 (o elemento neutro da multiplicação).
- Multiplique o resultado por cada número de 2 até n.
- Para n = 0 ou 1 o laço não roda e o resultado continua 1, que é a resposta certa.
- Variação: a versão recursiva é fatorial(n) = n × fatorial(n-1), com fatorial(0) = 1 como caso base.

## Pseudocódigo
```
função fatorial(n)
    se n < 0: erro
    resultado ← 1
    para i de 2 até n:
        resultado ← resultado × i
    retorne resultado
```

## Código
```python
def fatorial(n):
    if n < 0:
        raise ValueError("n deve ser >= 0")
    resultado = 1
    for i in range(2, n + 1):
        resultado *= i
    return resultado
```
```javascript
function fatorial(n) {
  if (n < 0) throw new Error("n deve ser >= 0");
  let resultado = 1;
  for (let i = 2; i <= n; i++) resultado *= i;
  return resultado;
}
```
```go
func fatorial(n int) int {
	resultado := 1
	for i := 2; i <= n; i++ {
		resultado *= i
	}
	return resultado
}
```
```java
static long fatorial(int n) {
    if (n < 0) throw new IllegalArgumentException("n deve ser >= 0");
    long resultado = 1;
    for (int i = 2; i <= n; i++) resultado *= i;
    return resultado;
}
```
```csharp
static long Fatorial(int n)
{
    if (n < 0) throw new ArgumentException("n deve ser >= 0");
    long resultado = 1;
    for (int i = 2; i <= n; i++) resultado *= i;
    return resultado;
}
```
