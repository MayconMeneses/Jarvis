"""Padrões (regex, em português) que o motor local usa para entender comandos sem IA.

A ORDEM IMPORTA: o primeiro padrão que casar vence. Comandos mais específicos vêm antes dos genéricos
("pesquisa", "noticias"). Cada nome corresponde a um método `_nome` do LocalEngine ou a uma entrada em MODULOS.
"""

from jarvis.local import agenda_skills, ensino, instagram_skills, mcp_skills, perfil_usuario_skills
from jarvis.local.radar_skills import PADRAO as _RADAR

PATTERNS = [
    # Ferramentas externas do catálogo curado (mcp_skills.py): comandos bem específicos, antes de tudo.
    *mcp_skills.PADROES,
    # Radar de Notícias (radar_skills.py): ANTES de "noticias" e "pesquisa", que também casariam com "radar notícias".
    ("radar", _RADAR),
    # Perfil do usuário (perfil_usuario_skills.py): ver, atualizar e apagar com cartão de aprovação; antes de "vocabulario" e "perfil".
    ("perfil_usuario", perfil_usuario_skills.PADRAO),
    # Aprendizado do jeito de falar do usuário (ensino.py / evolucao.py): antes de "llm_status", que também casa "o que você aprendeu".
    ("esquecer_aprendizado", r"^(apag\w+|esquec\w+|limp\w+|zer\w+)\s+(tudo\s+)?(o que\s+)?(voce\s+)?(aprendeu\s+)?(sobre\s+)?(como eu falo|meu jeito de falar|meu vocabulario|meus apelidos|os meus apelidos)$"),
    ("vocabulario", r"^(meu vocabulario|meus apelidos|o que (voce )?aprendeu (sobre|com|de) (como eu falo|meu jeito( de falar)?|mim|eu)|o que (voce )?aprendeu comigo|aprendeu alguma coisa (sobre|com) (mim|eu)|quais (frases|apelidos) (voce )?aprendeu)$"),
    ("evolucao_relatorio", r"^(como (voce )?(esta|ta|estou) evoluindo|relatorio de evolucao|qual (a )?(sua )?taxa de entendimento)$"),
    ("ensinar", ensino.PADRAO_ENSINAR),
    *agenda_skills.PADROES,  # agenda, e-mails, notícias de X e bom dia (jarvis/local/agenda_skills.py)
    *instagram_skills.PADROES,  # analista de Instagram (instagram_skills.py): antes de tudo, comandos bem específicos
    ("uso_ia", r"\b(quanto (eu )?(gastei|gasto|usei)(?! (no|na|nos|nas|com|em|de|do|da|dos|das|pra|para) (?!ia\b|claude|tokens?|gemini|nvidia|hoje|semana|mes|ultim|total|tudo|sempre|esse|este|essa|esta|nesse|neste|\d))|cota d[oa] claude|uso d[aeo] (ia|claude|tokens)|gasto com (ia|claude)|tokens (gastos|usados))\b"),
    ("sessoes", r"\bsess(ao|oes)\b.*\b(claude|code|esperando|aguardando|parada)\b|\bclaude code\b.*\b(esperando|aguardando)\b"),
    ("dashboard", r"^(cri[ae]|faca|fazer|faz|ger[ae]|gerar|mont[ae]|montar)\s+(um\s+|o\s+)?dashboard(\s+(de|do|da|dos|das|com|para|pra)(\s+.+)?)?$"),
    ("anotar_projeto", r"^anot\w*\s+(no|na|ao|em)\s+(projeto\s+)?.+?\s+que\s+.+$"),
    ("ficha", r"^(ficha|anotacoes)\s+(do\s+)?projeto\s+.+$"),
    ("projetos", r"^(meus projetos|quais (sao )?(os )?(meus )?projetos|lista\w*\s+(os\s+)?(meus\s+)?projetos)$"),
    ("perfil", r"^((meu|minha)\s+(stack|nivel|modalidade|ingles|cidade)\s*(e|eh|sao|:|=)\s*.+|(quero\s+)?evit\w+\s+.+)$"),
    ("memoria", r"^(o que voce (sabe|lembra)( sobre| de| do| da)?\b.*|(busqu\w*|procur\w*|pesquis\w*)\s+(na|nas|em)\s+(minha\s+)?(memoria|notas)\b.*)$"),
    ("lembrar", r"^(lembr\w*|anot\w*|guard\w*|memoriz\w*)\s+(de\s+)?(que\s+)?.{3,}$"),
    # Habilidades de programador (jarvis/local/habilidades_skills.py): avaliar projetos, evoluir, checklists.
    ("revisar", r"^(revis\w+|analis\w+|avali\w+)\s+(este|esse|o|a)\s+(diff|patch|trecho|pull request|codigo abaixo|codigo a seguir)\b[\s\S]*$"),
    ("avaliar_projeto", r"^(avali\w+|revis\w+|analis\w+|audit\w+)\s+(o\s+|a\s+)?(projeto|codigo|repositorio|sistema|[a-z]:\\).*$|"
                        r"^(avali\w+|revis\w+)\s+(o\s+|a\s+)?(voce mesma|a si mesma|si mesma|seu proprio codigo|seu codigo|proprio codigo)\b.*$"),
    ("habilidades", r"^(quais (sao )?(as )?(minhas |suas )?habilidades.*|minhas habilidades|suas habilidades|habilidades de programador.*|"
                    r"que habilidades.*|lista de habilidades)$"),
    ("evoluir", r"^(o que (devo|eu devo|posso|preciso) (estudar|evoluir|melhorar|praticar).*|qual (e )?(a )?(minha |sua )?proxima habilidade.*|"
                r"proxima habilidade.*|(qual (e )?(o )?|me de (o )?)?treino (da|de) semana.*|como (evoluir|melhorar|praticar)( como programador| minhas habilidades)?.*|plano de (estudo|evolucao).*)$"),
    ("checklist", r"^(checklist|lista de verificacao)\s+.+$"),
    # Programação (jarvis/local/dev_skills.py): criar sistemas, comparar, recomendar e explicar tecnologias.
    # Engenharia e UX (engenharia_skills.py) e cérebro local, aprender e avaliar (llm_skills.py).
    ("criar_com_ia", r"^(cri[ae]|desenvolv\w+|programe)\b.*\b(com (a )?ia( local)?|com o (cerebro|modelo) local|com a llm|pensando)\b.*$"),
    ("avaliar_llm", r"^(avali\w+|test\w+)\s+(o |a )?(cerebro|modelo|llm)( local)?\b.*$"),
    ("aprender", r"^(aprend\w+|estud\w+)\s+(sobre|a respeito de)\s+.{3,}$"),
    ("llm_instalar", r"^(instal\w+|baix\w+|lig\w+|ativ\w+)\s+(o |a )?(cerebro|modelo|ia|llm)( generativ\w+)? (local|proprio|proprio)\b.*$"),
    ("llm_status", r"(cerebro|modelo|llm) local|o que (voce )?(aprendeu|estudou)|aprendizado (automatico|autonomo)|(aprenda|estude) sozinha"),
    ("criar_sistema", r"^(cri[ae]|faca|fazer|faz|mont[ae]|ger[ae]|gerar|inici[ae]|comec[ae]|desenvolv\w+)\s+(um|uma)?\s*(novo\s+|nova\s+)?(sistema|projeto|app|aplicacao|site|api)\b.*$"),
    ("comparar", r"^(compar\w+|diferenca entr[ae]|qual (e )?a diferenca entr[ae]|qual (e )?melhor|o que (e )?melhor)\b.+|\b(vs|versus)\b"),
    ("recomendar", r"^(qual|que|quais)\s+(stack|tecnologia|tecnologias|linguagem|linguagens|framework|frameworks|banco|bancos)\b.*|"
                   r"^(recomend\w+|sugir\w+|indic\w+)\s+(uma?\s+)?(stack|tecnologia|linguagem|framework)\b.*|"
                   r"^(o que|qual)\s+(devo|eu devo|posso)\s+usar\b.*"),
    ("padrao", r"\b(padroes? de projeto|design patterns?|padrao (strategy|observer|factory|decorator|adapter|repository|command|builder))\b"),
    ("ux_ferramenta", r"^(?=.*(#[0-9a-f]{3}|\b[0-9a-f]{6}\b)).*\b(contraste|paleta|tokens?)\b|\b(escala tipografica|escala de tipos)\b"),
    ("gerar", r"^(cri[ae]|ger[ae]|gerar|faca|escrev\w+|mont[ae])\s+(um|uma|o|a)?\s*(tabela|esquema sql|adr|registro de decisao|historia de usuario|openapi|swagger|workflow|pipeline|dockerfile|editorconfig)\b.*$"),
    ("algoritmo", r"^(como (fazer|faco|escrever|implementar|programar|criar|calcular)|escreva|escrever|mostre|mostra|me mostre|me de|exemplo de|algoritmo (de|para)|codigo (de|para)|implemente|programa (de|para))\b.+$"),
    ("logica", r"^(como (resolver|resolvo|pensar|raciocinar)\b.*|me ajuda(r)? a (resolver|pensar)\b.*|logica de programacao|quais (conceitos|algoritmos)\b.*|que (conceitos|algoritmos)\b.*)$"),
    ("tecnologia", r"^(o que (e|sao)|que (e|sao)|fale sobre|me fale sobre|explique|explica|me explica|descreva|conte sobre)\s+(?P<tema>.+)$"),
    ("abrir", r"^(abr[ae]|abrir|abre pra mim|inici[ae]|execut[ae]|entr[ae] n[oa])\s+(?P<alvo>.+)$"),
    ("hora", r"\b(que horas?|hora atual|horas sao)\b"), ("data", r"\b(que dia e hoje|data de hoje|qual (a|e a) data|que dia e)\b"),
    ("processos", r"\b(processos|programas)\b.*\b(pesad\w*|mais us\w*|consum\w*)\b"),
    ("pc", r"\b(como (esta|ta) (o\s+)?(meu\s+)?(pc|computador)|status do (pc|computador)|uso de (ram|cpu|memoria|disco)|"
           r"memoria ram|quanto de (ram|memoria|disco))\b"),
    ("clima", r"\b(clima|previsao do tempo|vai chover|temperatura)\b(\s+(em|de|no|na)\s+(?P<cidade>.+))?"),
    ("noticias", r"\bnoticias?\b"),
    # Só pedidos de vagas ("lembre que prefiro vagas remotas" não é um pedido).
    ("vagas", r"^((tem|ha|existe\w*|quero|ver|mostr\w*|me mostr\w*|procur\w*|busc\w*|busqu\w*|lista\w*|quais)\b.{0,25}\bvagas?\b|vagas?\b)"),
    ("ajuda", r"^(ajuda|o que voce (faz|sabe fazer)|comandos|me ajuda)$"),
    ("pesquisa", r"^(pesquis\w*|procur\w*|busc\w*|busqu\w*|me fale sobre|fale sobre)\s+"
                 r"(informac\w+\s+)?(sobre\s+|de\s+)?(?P<tema>.+)$"),
]
