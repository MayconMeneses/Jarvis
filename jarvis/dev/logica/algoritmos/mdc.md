nome: MDC (máximo divisor comum)
aliases: mdc, maximo divisor comum, máximo divisor comum, gcd, euclides
problema: Achar o maior número que divide a e b sem deixar resto (algoritmo de Euclides).
complexidade: tempo O(log(min(a, b))), espaço O(1)
funcoes: python=mdc; javascript=mdc; go=mdc; java=mdc; csharp=Mdc
casos: [[[48, 18], 6], [[7, 13], 1], [[100, 10], 10], [[0, 5], 5]]
go_teste: fmt.Println(mdc(48, 18), mdc(7, 13), mdc(100, 10), mdc(0, 5))
go_saida: 6 1 10 5

## Ideia
- Propriedade: mdc(a, b) = mdc(b, a mod b).
- Repita trocando (a, b) por (b, resto da divisão) até o resto ser 0.
- Quando b chega a 0, a resposta é a.

## Pseudocódigo
```
função mdc(a, b)
    enquanto b ≠ 0:
        (a, b) ← (b, a mod b)
    retorne a
```

## Código
```python
def mdc(a, b):
    while b != 0:
        a, b = b, a % b
    return a
```
```javascript
function mdc(a, b) {
  while (b !== 0) [a, b] = [b, a % b];
  return a;
}
```
```go
func mdc(a, b int) int {
	for b != 0 {
		a, b = b, a%b
	}
	return a
}
```
```java
static int mdc(int a, int b) {
    while (b != 0) {
        int resto = a % b;
        a = b;
        b = resto;
    }
    return a;
}
```
```csharp
static int Mdc(int a, int b)
{
    while (b != 0)
    {
        int resto = a % b;
        a = b;
        b = resto;
    }
    return a;
}
```
