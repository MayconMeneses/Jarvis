"""Oficina: o IDE da Jarvis. Escrever, rodar, testar e (com IA) criar código, vendo o resultado na hora.

- sandbox.py: executa código em processo separado, em pasta temporária, com tempo, memória e saída limitados.
- espaco.py: arquivos da Oficina (uma pasta por projeto) com histórico de versões para desfazer.
- ia.py: "criar com IA": planeja, escreve, roda os testes num sandbox e corrige, mostrando o resultado.

Segurança: nada roda sozinho. Rodar e testar são cliques do usuário; o código da IA só é executado no sandbox, e o sandbox NÃO
bloqueia a rede nem protege contra código malicioso feito de propósito. Ele evita acidentes (laço infinito, memória estourada,
apagar arquivos do usuário por engano), não substitui revisar o código antes de rodar.
"""
