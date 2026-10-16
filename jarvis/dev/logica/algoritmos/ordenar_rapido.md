nome: Quicksort (ordenação rápida)
aliases: quicksort, quick sort, ordenacao rapida, ordenação rápida, ordenar rapido, ordenar rápido
problema: Ordenar uma lista com "dividir e conquistar": escolhe um pivô, separa menores e maiores, e ordena cada parte recursivamente.
complexidade: tempo O(n log n) em média, O(n²) no pior caso; espaço O(n) nesta versão simples
funcoes: python=ordenar_rapido; javascript=ordenarRapido; go=ordenarRapido; java=ordenarRapido; csharp=OrdenarRapido
casos: [[[[3, 6, 1, 8, 2, 9, 2]], [1, 2, 2, 3, 6, 8, 9]], [[[]], []], [[[1]], [1]], [[[5, 4, 3, 2, 1]], [1, 2, 3, 4, 5]]]
go_teste: fmt.Println(ordenarRapido([]int{3, 6, 1, 8, 2, 9, 2}), ordenarRapido([]int{}), ordenarRapido([]int{1}), ordenarRapido([]int{5, 4, 3, 2, 1}))
go_saida: [1 2 2 3 6 8 9] [] [1] [1 2 3 4 5]

## Ideia
- Caso base: lista com 0 ou 1 elemento já está ordenada (é o que PARA a recursão).
- Escolha um pivô (aqui, o elemento do meio).
- Separe em três grupos: menores que o pivô, iguais e maiores.
- Ordene os menores e os maiores com a própria função (recursão) e junte: menores + iguais + maiores.
- Por que é rápido: em média cada passo divide o problema em duas metades, como na busca binária.

## Pseudocódigo
```
função ordenarRapido(lista)
    se tamanho(lista) ≤ 1: retorne lista
    pivo ← lista[meio]
    menores ← elementos < pivo
    iguais ← elementos = pivo
    maiores ← elementos > pivo
    retorne ordenarRapido(menores) + iguais + ordenarRapido(maiores)
```

## Código
```python
def ordenar_rapido(lista):
    if len(lista) <= 1:
        return list(lista)
    pivo = lista[len(lista) // 2]
    menores = [x for x in lista if x < pivo]
    iguais = [x for x in lista if x == pivo]
    maiores = [x for x in lista if x > pivo]
    return ordenar_rapido(menores) + iguais + ordenar_rapido(maiores)
```
```javascript
function ordenarRapido(lista) {
  if (lista.length <= 1) return [...lista];
  const pivo = lista[Math.floor(lista.length / 2)];
  const menores = lista.filter((x) => x < pivo);
  const iguais = lista.filter((x) => x === pivo);
  const maiores = lista.filter((x) => x > pivo);
  return [...ordenarRapido(menores), ...iguais, ...ordenarRapido(maiores)];
}
```
```go
func ordenarRapido(lista []int) []int {
	if len(lista) <= 1 {
		return append([]int{}, lista...)
	}
	pivo := lista[len(lista)/2]
	var menores, iguais, maiores []int
	for _, x := range lista {
		switch {
		case x < pivo:
			menores = append(menores, x)
		case x == pivo:
			iguais = append(iguais, x)
		default:
			maiores = append(maiores, x)
		}
	}
	resultado := ordenarRapido(menores)
	resultado = append(resultado, iguais...)
	return append(resultado, ordenarRapido(maiores)...)
}
```
```java
static List<Integer> ordenarRapido(List<Integer> lista) {
    if (lista.size() <= 1) return new ArrayList<>(lista);
    int pivo = lista.get(lista.size() / 2);
    List<Integer> menores = new ArrayList<>(), iguais = new ArrayList<>(), maiores = new ArrayList<>();
    for (int x : lista) {
        if (x < pivo) menores.add(x);
        else if (x == pivo) iguais.add(x);
        else maiores.add(x);
    }
    List<Integer> resultado = ordenarRapido(menores);
    resultado.addAll(iguais);
    resultado.addAll(ordenarRapido(maiores));
    return resultado;
}
```
```csharp
static List<int> OrdenarRapido(List<int> lista)
{
    if (lista.Count <= 1) return new List<int>(lista);
    int pivo = lista[lista.Count / 2];
    var menores = lista.Where(x => x < pivo).ToList();
    var iguais = lista.Where(x => x == pivo).ToList();
    var maiores = lista.Where(x => x > pivo).ToList();
    var resultado = OrdenarRapido(menores);
    resultado.AddRange(iguais);
    resultado.AddRange(OrdenarRapido(maiores));
    return resultado;
}
```
