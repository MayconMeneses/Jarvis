nome: Número primo
aliases: primo, numero primo, número primo, eh primo, é primo, verificar primo
problema: Dizer se n é primo (maior que 1 e divisível só por 1 e por ele mesmo).
complexidade: tempo O(√n), espaço O(1)
funcoes: python=eh_primo; javascript=ehPrimo; go=ehPrimo; java=ehPrimo; csharp=EhPrimo
casos: [[[1], false], [[2], true], [[17], true], [[18], false], [[97], true], [[100], false]]
go_teste: fmt.Println(ehPrimo(1), ehPrimo(2), ehPrimo(17), ehPrimo(18), ehPrimo(97), ehPrimo(100))
go_saida: false true true false true false

## Ideia
- Números menores que 2 não são primos.
- Se n tem um divisor, ele tem um divisor menor ou igual a √n: só precisa testar até a raiz quadrada.
- Se algum i de 2 até √n divide n sem resto, n não é primo.
- Se nenhum dividiu, é primo.

## Pseudocódigo
```
função ehPrimo(n)
    se n < 2: retorne falso
    para i de 2 até raiz(n):
        se n mod i = 0: retorne falso
    retorne verdadeiro
```

## Código
```python
def eh_primo(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True
```
```javascript
function ehPrimo(n) {
  if (n < 2) return false;
  for (let i = 2; i * i <= n; i++) {
    if (n % i === 0) return false;
  }
  return true;
}
```
```go
func ehPrimo(n int) bool {
	if n < 2 {
		return false
	}
	for i := 2; i*i <= n; i++ {
		if n%i == 0 {
			return false
		}
	}
	return true
}
```
```java
static boolean ehPrimo(int n) {
    if (n < 2) return false;
    for (int i = 2; (long) i * i <= n; i++) {
        if (n % i == 0) return false;
    }
    return true;
}
```
```csharp
static bool EhPrimo(int n)
{
    if (n < 2) return false;
    for (int i = 2; (long)i * i <= n; i++)
    {
        if (n % i == 0) return false;
    }
    return true;
}
```
