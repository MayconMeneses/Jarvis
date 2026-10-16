nome: Inverter um texto
aliases: inverter, inverter texto, inverter string, reverter texto, reverse
problema: Devolver o texto de trás para frente ("abc" vira "cba").
complexidade: tempo O(n), espaço O(n)
funcoes: python=inverter; javascript=inverter; go=inverter; java=inverter; csharp=Inverter
casos: [[["abc"], "cba"], [[""], ""], [["Jarvis"], "sivraJ"], [["a"], "a"]]
go_teste: fmt.Println(inverter("abc") == "cba", inverter("") == "", inverter("Jarvis"), inverter("a"))
go_saida: true true sivraJ a

## Ideia
- Percorra o texto da esquerda para a direita.
- A cada caractere, coloque-o NA FRENTE do que já foi montado.
- No fim, o primeiro caractere ficou por último: o texto está invertido.
- Atalhos prontos existem (texto[::-1] em Python), mas conhecer o laço ensina a lógica.

## Pseudocódigo
```
função inverter(texto)
    resultado ← ""
    para cada caractere em texto:
        resultado ← caractere + resultado
    retorne resultado
```

## Código
```python
def inverter(texto):
    resultado = ""
    for caractere in texto:
        resultado = caractere + resultado
    return resultado
```
```javascript
function inverter(texto) {
  let resultado = "";
  for (const caractere of texto) resultado = caractere + resultado;
  return resultado;
}
```
```go
func inverter(texto string) string {
	letras := []rune(texto)
	for i, j := 0, len(letras)-1; i < j; i, j = i+1, j-1 {
		letras[i], letras[j] = letras[j], letras[i]
	}
	return string(letras)
}
```
```java
static String inverter(String texto) {
    StringBuilder resultado = new StringBuilder();
    for (int i = texto.length() - 1; i >= 0; i--) resultado.append(texto.charAt(i));
    return resultado.toString();
}
```
```csharp
static string Inverter(string texto)
{
    var letras = texto.ToCharArray();
    Array.Reverse(letras);
    return new string(letras);
}
```
