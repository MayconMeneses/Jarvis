nome: FizzBuzz
aliases: fizzbuzz, fizz buzz
problema: De 1 até n: múltiplos de 3 viram "Fizz", de 5 viram "Buzz", de ambos "FizzBuzz"; os outros ficam como número. Clássico de condicionais e laços.
complexidade: tempo O(n), espaço O(n)
funcoes: python=fizzbuzz; javascript=fizzbuzz; go=fizzbuzz; java=fizzbuzz; csharp=FizzBuzz
casos: [[[5], ["1", "2", "Fizz", "4", "Buzz"]], [[15], ["1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8", "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz"]], [[0], []]]
go_teste: fmt.Println(fizzbuzz(5), len(fizzbuzz(0)), fizzbuzz(15)[14])
go_saida: [1 2 Fizz 4 Buzz] 0 FizzBuzz

## Ideia
- Percorra de 1 a n.
- A ordem dos testes importa: verifique "múltiplo de 3 E de 5" PRIMEIRO (senão cai no Fizz ou no Buzz e nunca imprime FizzBuzz).
- Use o resto da divisão (módulo): i mod 3 = 0 significa "múltiplo de 3".
- Se nenhuma regra valer, o texto é o próprio número.

## Pseudocódigo
```
função fizzbuzz(n)
    saida ← lista vazia
    para i de 1 até n:
        se i mod 15 = 0: adicione "FizzBuzz"
        senão se i mod 3 = 0: adicione "Fizz"
        senão se i mod 5 = 0: adicione "Buzz"
        senão: adicione texto(i)
    retorne saida
```

## Código
```python
def fizzbuzz(n):
    saida = []
    for i in range(1, n + 1):
        if i % 15 == 0:
            saida.append("FizzBuzz")
        elif i % 3 == 0:
            saida.append("Fizz")
        elif i % 5 == 0:
            saida.append("Buzz")
        else:
            saida.append(str(i))
    return saida
```
```javascript
function fizzbuzz(n) {
  const saida = [];
  for (let i = 1; i <= n; i++) {
    if (i % 15 === 0) saida.push("FizzBuzz");
    else if (i % 3 === 0) saida.push("Fizz");
    else if (i % 5 === 0) saida.push("Buzz");
    else saida.push(String(i));
  }
  return saida;
}
```
```go
import "strconv"

func fizzbuzz(n int) []string {
	saida := []string{}
	for i := 1; i <= n; i++ {
		switch {
		case i%15 == 0:
			saida = append(saida, "FizzBuzz")
		case i%3 == 0:
			saida = append(saida, "Fizz")
		case i%5 == 0:
			saida = append(saida, "Buzz")
		default:
			saida = append(saida, strconv.Itoa(i))
		}
	}
	return saida
}
```
```java
static List<String> fizzbuzz(int n) {
    List<String> saida = new ArrayList<>();
    for (int i = 1; i <= n; i++) {
        if (i % 15 == 0) saida.add("FizzBuzz");
        else if (i % 3 == 0) saida.add("Fizz");
        else if (i % 5 == 0) saida.add("Buzz");
        else saida.add(String.valueOf(i));
    }
    return saida;
}
```
```csharp
static List<string> FizzBuzz(int n)
{
    var saida = new List<string>();
    for (int i = 1; i <= n; i++)
    {
        if (i % 15 == 0) saida.Add("FizzBuzz");
        else if (i % 3 == 0) saida.Add("Fizz");
        else if (i % 5 == 0) saida.Add("Buzz");
        else saida.Add(i.ToString());
    }
    return saida;
}
```
