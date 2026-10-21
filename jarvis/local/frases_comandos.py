"""Frases-exemplo dos comandos que o motor já executa: alimentam o casador quando nenhuma regra (regex) casa.

Cada intenção: (rótulo para "Você quis dizer", exemplo de como pedir, executa direto?, frases).
`executa` só é True para comandos SEM argumentos e sem efeito colateral (ler/mostrar): com confiança alta o casador os roda;
os demais (abrir, pesquisar, anotar...) só aparecem como sugestão, porque dependem de um nome que a frase não trouxe.
Estas frases NÃO são as da bateria de validação (jarvis/eval/data/comandos_validacao.json): a validação mede de verdade.
"""

from __future__ import annotations

INTENCOES: dict[str, tuple[str, str, bool, list[str]]] = {
    "hora": ("ver a hora", "que horas são", True, [
        "que horas são", "me diz as horas", "qual é o horário agora", "tem hora aí", "me fala o horário", "horário atual",
        "marca quantas horas", "pode me dizer as horas"]),
    "data": ("ver a data de hoje", "que dia é hoje", True, [
        "que dia é hoje", "qual é a data de hoje", "em que dia estamos", "hoje é que dia da semana", "me diz a data",
        "que dia do mês é hoje", "dia da semana hoje", "estamos em que dia"]),
    "pc": ("ver o estado do PC", "como está o PC", True, [
        "como está o meu computador", "o pc está lento", "meu computador está travando", "ver uso de memória e processador",
        "quanta memória ram está livre", "espaço livre no disco", "saúde do computador", "como anda a máquina",
        "status da máquina", "o notebook está pesado"]),
    "processos": ("ver os programas pesados", "programas pesados", True, [
        "o que está pesando o computador", "quais programas estão gastando memória", "o que está usando a cpu",
        "o que está deixando o pc lento", "quem está consumindo recursos", "me mostra os processos mais pesados",
        "lista de programas que mais gastam"]),
    "clima": ("ver o clima", "clima em Fortaleza", True, [
        "vai fazer sol amanhã", "como está o tempo lá fora", "preciso de guarda-chuva", "tá calor hoje", "vai esfriar hoje",
        "previsão para hoje", "como vai estar o tempo", "vai ter chuva"]),
    "noticias": ("ver as notícias", "notícias de tecnologia", True, [
        "o que está acontecendo no mundo", "quais as novidades de hoje", "me atualiza das notícias", "manchetes do dia",
        "o que saiu de novo hoje", "me conta as últimas notícias", "novidades em tecnologia"]),
    "vagas": ("ver vagas", "tem vagas para mim", True, [
        "tem emprego para mim", "oportunidades de trabalho para dev", "vagas de desenvolvedor", "tem alguma vaga nova",
        "me mostra oportunidades de emprego", "vagas remotas de programação"]),
    "ajuda": ("ver a ajuda", "ajuda", True, [
        "o que você sabe fazer", "o que você consegue fazer", "quais são seus comandos", "como eu uso você",
        "me mostra suas funções", "que comandos existem"]),
    "projetos": ("listar meus projetos", "meus projetos", True, [
        "quais projetos eu tenho", "lista meus projetos", "mostra os projetos cadastrados", "quais são os meus projetos"]),
    "sessoes": ("ver as sessões do Claude Code", "alguma sessão está me esperando", True, [
        "o claude code está esperando alguma coisa", "tem sessão do claude parada", "alguma sessão precisa de mim",
        "o claude terminou", "o claude code está aguardando"]),
    "habilidades": ("ver minhas habilidades de programador", "quais habilidades de programador", True, [
        "lista as habilidades de programador", "que habilidades você acompanha", "habilidades de programação"]),
    "evoluir": ("saber o que estudar", "o que devo estudar", True, [
        "qual a próxima habilidade", "o que eu deveria praticar", "me dá o treino da semana", "o que devo melhorar como programador",
        "sugere o que estudar agora"]),
    "uso_ia": ("ver o uso de IA", "cota do Claude", True, [
        "quanto de ia eu usei", "quanto já gastei de tokens", "como está meu limite do claude", "qual o custo das ias",
        "quantos tokens usei hoje", "o limite do claude está acabando"]),
    "bom_dia": ("receber o resumo do dia", "bom dia", True, [
        "resumo do meu dia", "me atualiza do dia", "como está o meu dia", "quero o resumo da manhã", "o que tem para hoje"]),
    "agenda_hoje": ("ver a agenda de hoje", "minha agenda", True, [
        "o que eu tenho marcado hoje", "tenho reunião hoje", "quais meus compromissos hoje", "mostra a agenda de hoje",
        "tem algum evento hoje", "como está meu dia na agenda"]),
    "agenda_semana": ("ver a agenda da semana", "agenda da semana", True, [
        "o que tenho essa semana", "compromissos dos próximos dias", "agenda dos próximos dias", "como está minha semana",
        "o que está marcado nessa semana"]),
    "agenda_proximo": ("ver o próximo compromisso", "próximo compromisso", True, [
        "qual a minha próxima reunião", "o que vem agora na agenda", "quando é meu próximo evento", "próxima reunião"]),
    "emails": ("ver meus e-mails", "meus e-mails", True, [
        "chegou algum email", "como está minha caixa de entrada", "tem email novo", "mostra meus emails", "resumo dos emails",
        "tem mensagem nova no email"]),
    "email_importante": ("ver e-mails importantes", "tem e-mail importante", True, [
        "algum email urgente", "tem algo urgente no email", "algum email precisa de resposta", "emails que pedem ação"]),
    "radar": ("gerar o Radar de Notícias", "radar", True, [
        "me dá o boletim do radar", "quero o radar de hoje", "gerar o boletim do meu nicho", "radar de notícias"]),
    "vocabulario": ("ver o que aprendi sobre como você fala", "meu vocabulário", True, [
        "o que você aprendeu comigo", "quais frases você aprendeu", "mostra meus apelidos", "como você está evoluindo",
        "o que você aprendeu do meu jeito de falar"]),
    # Precisam de um nome ou assunto: só viram sugestão.
    "abrir": ("abrir um programa, site ou pasta", "abre o WhatsApp", False, [
        "abrir programa", "inicia um aplicativo", "quero abrir um site", "abre uma pasta", "lança o programa"]),
    "pesquisa": ("pesquisar na internet", "pesquise sobre Docker", False, [
        "pesquisar na internet", "procura isso na web", "busca informações na internet", "quero saber sobre um assunto"]),
    "lembrar": ("guardar algo na memória", "lembre que eu prefiro vagas remotas", False, [
        "guarda isso na memória", "anota uma coisa para mim", "memoriza uma informação", "registra um fato"]),
    "memoria": ("consultar a memória", "o que você sabe sobre mim", False, [
        "o que você lembra de mim", "busca nas minhas notas", "o que tem anotado sobre isso"]),
    "tecnologia": ("explicar uma tecnologia", "o que é React", False, [
        "explica uma tecnologia", "o que é uma linguagem de programação", "me explica um framework"]),
    "comparar": ("comparar tecnologias", "compare Django e FastAPI", False, [
        "qual a diferença entre duas tecnologias", "compara essas duas ferramentas", "qual é melhor entre elas"]),
    "criar_sistema": ("criar um sistema pronto", "crie um sistema chamado Loja com FastAPI e React", False, [
        "monta um projeto novo para mim", "cria um app novo", "quero começar um sistema"]),
    "avaliar_projeto": ("avaliar um projeto", "avalie o projeto Loja", False, [
        "revisa um projeto", "audita meu código", "avalia a qualidade do meu projeto"]),
}


def frases(intencao: str) -> list[str]:
    return INTENCOES[intencao][3]
