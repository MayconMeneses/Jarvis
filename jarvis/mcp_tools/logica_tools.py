"""Lógica de programação: conceitos, algoritmos prontos em várias linguagens e o método de resolução."""

from __future__ import annotations

from jarvis.dev import logica
from jarvis.mcp_tools.core import server


@server.tool()
def explicar_conceito(nome: str) -> str:
    """Explica um conceito de lógica e programação (variáveis, condicionais, laços, funções, recursão, listas,
    dicionários, pilha, fila, árvores, grafos, ordenação, busca, Big-O, POO, testes, depuração, banco de dados,
    API REST, git, segurança, arquitetura...) com passos, analogia, exemplo, erros comuns e exercícios.
    Base curada e offline."""
    item = logica.concept(nome)
    if item is None:
        return f"Não tenho \"{nome}\" entre os conceitos. " + logica.concepts_overview()
    return logica.describe_concept(item)


@server.tool()
def exemplo_de_algoritmo(nome: str, linguagem: str = "python") -> str:
    """Mostra um algoritmo clássico (fatorial, fibonacci, primo, mdc, palíndromo, inverter, maior elemento,
    média, busca linear/binária, ordenação por bolha/quicksort, contar palavras, fizzbuzz, decimal→binário):
    ideia, pseudocódigo, complexidade e código em Python, JavaScript, Go, Java ou C#. Python, JavaScript e Go
    são testados com casos de entrada e saída."""
    item = logica.algorithm(nome)
    if item is None:
        return f"Não tenho o algoritmo \"{nome}\" pronto. " + logica.algorithms_overview()
    return logica.show(item, logica.language_in(linguagem, "python") if linguagem else "python")


@server.tool()
def como_resolver_problema(problema: str = "") -> str:
    """O roteiro de 9 passos para resolver qualquer problema de programação (entender, exemplos, estratégia, dividir,
    pseudocódigo, implementar, testar, melhorar, refletir). Se o problema for um clássico conhecido, já traz o algoritmo."""
    return logica.method(problema)


@server.tool()
def listar_conceitos_e_algoritmos() -> str:
    """Lista todos os conceitos de lógica e todos os algoritmos que a Jarvis sabe explicar e escrever."""
    return logica.concepts_overview() + "\n\n" + logica.algorithms_overview()
