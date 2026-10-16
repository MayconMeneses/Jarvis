nome: Decimal para binário
aliases: binario, binário, decimal para binario, decimal para binário, converter para binario, converter para binário, base 2
problema: Converter um inteiro não negativo para sua representação em binário (texto de 0 e 1).
complexidade: tempo O(log n), espaço O(log n)
funcoes: python=para_binario; javascript=paraBinario; go=paraBinario; java=paraBinario; csharp=ParaBinario
casos: [[[10], "1010"], [[0], "0"], [[255], "11111111"], [[1], "1"], [[8], "1000"]]
go_teste: fmt.Println(paraBinario(10), paraBinario(0), paraBinario(255), paraBinario(1), paraBinario(8))
go_saida: 1010 0 11111111 1 1000

## Ideia
- Divida o número por 2 repetidamente; o RESTO de cada divisão (0 ou 1) é um dígito binário.
- Os restos saem do dígito menos significativo para o mais: por isso cada novo dígito vai NA FRENTE do texto.
- Pare quando o número chegar a 0. O caso n = 0 é especial: a resposta é "0".
- Exemplo: 10 → restos 0,1,0,1 → lendo de trás para frente: 1010.

## Pseudocódigo
```
função paraBinario(n)
    se n = 0: retorne "0"
    resultado ← ""
    enquanto n > 0:
        resultado ← texto(n mod 2) + resultado
        n ← n ÷ 2 (divisão inteira)
    retorne resultado
```

## Código
```python
def para_binario(n):
    if n == 0:
        return "0"
    resultado = ""
    while n > 0:
        resultado = str(n % 2) + resultado
        n //= 2
    return resultado
```
```javascript
function paraBinario(n) {
  if (n === 0) return "0";
  let resultado = "";
  while (n > 0) {
    resultado = String(n % 2) + resultado;
    n = Math.floor(n / 2);
  }
  return resultado;
}
```
```go
import "strconv"

func paraBinario(n int) string {
	if n == 0 {
		return "0"
	}
	resultado := ""
	for n > 0 {
		resultado = strconv.Itoa(n%2) + resultado
		n /= 2
	}
	return resultado
}
```
```java
static String paraBinario(int n) {
    if (n == 0) return "0";
    StringBuilder resultado = new StringBuilder();
    while (n > 0) {
        resultado.insert(0, n % 2);
        n /= 2;
    }
    return resultado.toString();
}
```
```csharp
static string ParaBinario(int n)
{
    if (n == 0) return "0";
    var resultado = new System.Text.StringBuilder();
    while (n > 0)
    {
        resultado.Insert(0, n % 2);
        n /= 2;
    }
    return resultado.ToString();
}
```
