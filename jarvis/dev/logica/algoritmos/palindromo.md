nome: Palíndromo
aliases: palindromo, palíndromo, palindrome, eh palindromo, é palíndromo
problema: Dizer se um texto lê igual de trás para frente, ignorando maiúsculas, espaços e pontuação.
complexidade: tempo O(n), espaço O(n)
funcoes: python=eh_palindromo; javascript=ehPalindromo; go=ehPalindromo; java=ehPalindromo; csharp=EhPalindromo
casos: [[["Ana"], true], [["Socorram-me, subi no onibus em Marrocos"], true], [["Python"], false], [["Arara"], true]]
go_teste: fmt.Println(ehPalindromo("Ana"), ehPalindromo("Socorram-me, subi no onibus em Marrocos"), ehPalindromo("Python"), ehPalindromo("Arara"))
go_saida: true true false true

## Ideia
- Primeiro normalize: deixe só letras e números, tudo em minúsculas.
- Compare o texto limpo com ele mesmo invertido.
- Alternativa sem criar cópia: dois ponteiros, um no começo e outro no fim, andando para o centro.

## Pseudocódigo
```
função ehPalindromo(texto)
    limpo ← só letras e números de texto, em minúsculas
    retorne limpo = inverso(limpo)
```

## Código
```python
def eh_palindromo(texto):
    limpo = "".join(c.lower() for c in texto if c.isalnum())
    return limpo == limpo[::-1]
```
```javascript
function ehPalindromo(texto) {
  const limpo = texto.toLowerCase().replace(/[^\p{L}\p{N}]/gu, "");
  return limpo === [...limpo].reverse().join("");
}
```
```go
import (
	"strings"
	"unicode"
)

func ehPalindromo(texto string) bool {
	var letras []rune
	for _, c := range strings.ToLower(texto) {
		if unicode.IsLetter(c) || unicode.IsDigit(c) {
			letras = append(letras, c)
		}
	}
	for i, j := 0, len(letras)-1; i < j; i, j = i+1, j-1 {
		if letras[i] != letras[j] {
			return false
		}
	}
	return true
}
```
```java
static boolean ehPalindromo(String texto) {
    StringBuilder limpo = new StringBuilder();
    for (char c : texto.toLowerCase().toCharArray()) {
        if (Character.isLetterOrDigit(c)) limpo.append(c);
    }
    return limpo.toString().contentEquals(new StringBuilder(limpo).reverse());
}
```
```csharp
static bool EhPalindromo(string texto)
{
    var limpo = new string(texto.ToLower().Where(char.IsLetterOrDigit).ToArray());
    return limpo == new string(limpo.Reverse().ToArray());
}
```
