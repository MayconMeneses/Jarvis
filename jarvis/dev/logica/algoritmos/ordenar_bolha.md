nome: Ordenação por bolha (bubble sort)
aliases: bubble sort, ordenacao bolha, ordenação bolha, ordenar bolha, ordenacao por bolha, ordenação por bolha, ordenar lista, ordenar
problema: Colocar uma lista de números em ordem crescente trocando vizinhos fora de ordem.
complexidade: tempo O(n²) (O(n) se já estiver ordenada, com a parada antecipada), espaço O(1) além da cópia
funcoes: python=ordenar_bolha; javascript=ordenarBolha; go=ordenarBolha; java=ordenarBolha; csharp=OrdenarBolha
casos: [[[[5, 2, 9, 1]], [1, 2, 5, 9]], [[[]], []], [[[3, 3, 1]], [1, 3, 3]], [[[1, 2, 3]], [1, 2, 3]]]
go_teste: fmt.Println(ordenarBolha([]int{5, 2, 9, 1}), ordenarBolha([]int{}), ordenarBolha([]int{3, 3, 1}), ordenarBolha([]int{1, 2, 3}))
go_saida: [1 2 5 9] [] [1 3 3] [1 2 3]

## Ideia
- Passe pela lista comparando cada par de vizinhos; se estiverem na ordem errada, troque.
- Depois de uma passada completa, o MAIOR elemento já "flutuou" até o fim, como uma bolha.
- Repita as passadas; a cada uma o final ordenado cresce em 1 posição.
- Se uma passada inteira não trocar nada, a lista já está ordenada: pare.
- Bom para aprender; para listas grandes use o ordenador pronto da linguagem (sorted, sort) ou o quicksort.

## Pseudocódigo
```
função ordenarBolha(lista)
    copia ← cópia de lista
    repita:
        trocou ← falso
        para i de 0 até tamanho(copia) - 2:
            se copia[i] > copia[i+1]:
                troque copia[i] e copia[i+1]
                trocou ← verdadeiro
    até trocou = falso
    retorne copia
```

## Código
```python
def ordenar_bolha(lista):
    copia = list(lista)
    trocou = True
    while trocou:
        trocou = False
        for i in range(len(copia) - 1):
            if copia[i] > copia[i + 1]:
                copia[i], copia[i + 1] = copia[i + 1], copia[i]
                trocou = True
    return copia
```
```javascript
function ordenarBolha(lista) {
  const copia = [...lista];
  let trocou = true;
  while (trocou) {
    trocou = false;
    for (let i = 0; i < copia.length - 1; i++) {
      if (copia[i] > copia[i + 1]) {
        [copia[i], copia[i + 1]] = [copia[i + 1], copia[i]];
        trocou = true;
      }
    }
  }
  return copia;
}
```
```go
func ordenarBolha(lista []int) []int {
	copia := append([]int{}, lista...)
	trocou := true
	for trocou {
		trocou = false
		for i := 0; i < len(copia)-1; i++ {
			if copia[i] > copia[i+1] {
				copia[i], copia[i+1] = copia[i+1], copia[i]
				trocou = true
			}
		}
	}
	return copia
}
```
```java
static int[] ordenarBolha(int[] lista) {
    int[] copia = lista.clone();
    boolean trocou = true;
    while (trocou) {
        trocou = false;
        for (int i = 0; i < copia.length - 1; i++) {
            if (copia[i] > copia[i + 1]) {
                int temp = copia[i];
                copia[i] = copia[i + 1];
                copia[i + 1] = temp;
                trocou = true;
            }
        }
    }
    return copia;
}
```
```csharp
static int[] OrdenarBolha(int[] lista)
{
    int[] copia = (int[])lista.Clone();
    bool trocou = true;
    while (trocou)
    {
        trocou = false;
        for (int i = 0; i < copia.Length - 1; i++)
        {
            if (copia[i] > copia[i + 1])
            {
                (copia[i], copia[i + 1]) = (copia[i + 1], copia[i]);
                trocou = true;
            }
        }
    }
    return copia;
}
```
