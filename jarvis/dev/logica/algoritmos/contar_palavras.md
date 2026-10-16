nome: Contar palavras
aliases: contar palavras, frequencia de palavras, frequência de palavras, contagem de palavras, word count
problema: Contar quantas vezes cada palavra aparece num texto, ignorando maiúsculas e pontuação.
complexidade: tempo O(n), espaço O(k) para k palavras diferentes
funcoes: python=contar_palavras; javascript=contarPalavras; go=contarPalavras; java=contarPalavras; csharp=ContarPalavras
casos: [[["a casa e a casa"], {"a": 2, "casa": 2, "e": 1}], [["Oi, oi! Tudo bem?"], {"oi": 2, "tudo": 1, "bem": 1}], [[""], {}]]
go_teste: fmt.Println(contarPalavras("a casa e a casa"), contarPalavras("Oi, oi! Tudo bem?"), contarPalavras(""))
go_saida: map[a:2 casa:2 e:1] map[bem:1 oi:2 tudo:1] map[]

## Ideia
- Use um dicionário (mapa) palavra → contagem: é a estrutura certa para "contar coisas".
- Normalize: minúsculas, separe por espaços e tire a pontuação das pontas.
- Para cada palavra: se já está no dicionário, some 1; senão, comece em 1.
- Ignore pedaços vazios (sobram quando só havia pontuação).

## Pseudocódigo
```
função contarPalavras(texto)
    contagem ← dicionário vazio
    para cada palavra em dividir(minusculas(texto)):
        palavra ← tirar pontuação das pontas de palavra
        se palavra não é vazia:
            contagem[palavra] ← (contagem[palavra] ou 0) + 1
    retorne contagem
```

## Código
```python
def contar_palavras(texto):
    contagem = {}
    for palavra in texto.lower().split():
        palavra = palavra.strip(".,;:!?")
        if palavra:
            contagem[palavra] = contagem.get(palavra, 0) + 1
    return contagem
```
```javascript
function contarPalavras(texto) {
  const contagem = {};
  for (let palavra of texto.toLowerCase().split(/\s+/)) {
    palavra = palavra.replace(/^[.,;:!?]+|[.,;:!?]+$/g, "");
    if (palavra) contagem[palavra] = (contagem[palavra] ?? 0) + 1;
  }
  return contagem;
}
```
```go
import "strings"

func contarPalavras(texto string) map[string]int {
	contagem := map[string]int{}
	for _, palavra := range strings.Fields(strings.ToLower(texto)) {
		palavra = strings.Trim(palavra, ".,;:!?")
		if palavra != "" {
			contagem[palavra]++
		}
	}
	return contagem
}
```
```java
static Map<String, Integer> contarPalavras(String texto) {
    Map<String, Integer> contagem = new HashMap<>();
    for (String palavra : texto.toLowerCase().split("\\s+")) {
        palavra = palavra.replaceAll("^[.,;:!?]+|[.,;:!?]+$", "");
        if (!palavra.isEmpty()) contagem.merge(palavra, 1, Integer::sum);
    }
    return contagem;
}
```
```csharp
static Dictionary<string, int> ContarPalavras(string texto)
{
    var contagem = new Dictionary<string, int>();
    foreach (var bruta in texto.ToLower().Split(' ', StringSplitOptions.RemoveEmptyEntries))
    {
        var palavra = bruta.Trim('.', ',', ';', ':', '!', '?');
        if (palavra.Length > 0) contagem[palavra] = contagem.GetValueOrDefault(palavra) + 1;
    }
    return contagem;
}
```
