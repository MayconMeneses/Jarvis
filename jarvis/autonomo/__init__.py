"""Aprendizado autônomo: a Jarvis vai atrás, sozinha, dos assuntos sobre os quais mais conversamos.

- interesses.py: descobre os assuntos que o usuário mais pergunta (diário de pedidos) e os que a Jarvis ainda não conhece.
- estudar.py: pesquisa um assunto na internet, guarda o resumo (com fontes, "não verificado") e registra o que aprendeu.
- agendador.py: quando o PC está parado, estuda poucos assuntos por dia e faz uma avaliação semanal do cérebro local.

Regras de segurança: vem DESLIGADO; os assuntos vêm só do que o USUÁRIO conversou; só lê (nunca baixa nem executa nada); o texto de
sites é dado, nunca instrução; tudo vira nota visível, editável e apagável na janela de memória; há limite de assuntos por dia.
"""
