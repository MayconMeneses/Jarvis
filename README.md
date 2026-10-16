# Super Jarvis

Assistente pessoal para **Windows** que conversa por texto e por voz (em português), abre programas, cuida do PC
e do e-mail, pesquisa na internet, escreve código com o Claude Code e **continua funcionando mesmo sem nenhuma IA**.

- **Cérebros:** Claude (pela sua assinatura, via Claude Code), Gemini e NVIDIA como reserva e um **motor local sem IA** como último recurso.
- **Você no controle:** a IA só *propõe*. Mudar o PC, o e-mail ou o código só acontece depois do seu clique em **Aprovar**.
- **Privacidade:** a transcrição de voz é local; as chaves ficam no Gerenciador de Credenciais do Windows.
- **Leve:** pensada para um notebook comum (8 GB de RAM, sem GPU).

> Projeto pessoal em evolução. O plano original está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

## Instalar e rodar

**Desenvolvimento.** Requisitos: Python 3.11 e o Claude Code instalado e logado (`claude auth status`).

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m jarvis "Olá, Jarvis"
```

- `python -m jarvis` abre a janela (use `pythonw.exe` para não abrir o console).
- `python -m jarvis --texto` conversa no terminal (digite `sair` para encerrar).
- `python -m jarvis "pergunta"` responde uma vez no terminal.

### Instalador

**Instalar:** rode `dist\SuperJarvis-Setup-0.8.0.exe` (131 MB).
- Instala só para o seu usuário, em `%LOCALAPPDATA%\Programs\SuperJarvis`, sem pedir administrador.
- Cria atalho no menu Iniciar. O atalho na área de trabalho e o "Abrir a Jarvis quando o Windows iniciar" são opcionais.
- Avisa se o Claude Code não estiver instalado (e a janela da Jarvis avisa de novo, com o que muda, se faltar o Claude Code ou o git).
- Desinstale em Configurações > Aplicativos. Suas configurações, chaves e a memória (`%APPDATA%\SuperJarvis\memoria.db`) **são mantidas**.
- Só uma Jarvis abre por vez. Abrir de novo apenas avisa que ela já está na bandeja.

Dois executáveis na pasta do programa:
- `Jarvis.exe`: janela, bandeja e voz.
- `jarvis-cli.exe`: terminal. Use `jarvis-cli.exe --conectar gmail` e `jarvis-cli.exe --chave gemini` no lugar de `python -m jarvis ...`. Também é o servidor MCP usado pelo Claude.

**O que vai dentro do instalador e o que não vai**
- **Dentro:** o programa e todas as bibliotecas, a memória (SQLite), o painel de dashboards, o modelo "Hey Jarvis" e o **modelo de voz Whisper**. O modelo fica em `<pasta do programa>\modelos` e a Jarvis o usa dali, **sem depender do cache de ninguém**.
- **Para gerar o instalador com o modelo** (funciona offline desde a 1ª abertura, ~0,5 GB maior): `python packaging\baixar_modelo.py` (copia o `small`, o padrão; use `base` para ~145 MB; `--nenhum` para um instalador pequeno) e depois os dois comandos abaixo.
- **Sem o modelo no instalador**, a Jarvis baixa o `small` (~465 MB) uma vez, na primeira abertura, para `%LOCALAPPDATA%\SuperJarvis\modelos`, e mostra o andamento no topo da janela. Sem internet nessa hora, a voz avisa o que fazer (a conversa por texto continua).
- **Fora (não dá para embutir):** o **Claude Code** (usa a sua assinatura e o seu login) e o **git**. A Jarvis os procura ao abrir, inclusive em `~\.local\bin`; se faltarem, mostra na janela o que muda e onde instalar. Sem o Claude Code, usa Gemini/NVIDIA (se houver chave) ou o modo independente.
- **Fora de propósito:** chaves, contas de e-mail e a memória do usuário (`%APPDATA%\SuperJarvis`), que sobrevivem a atualizar e desinstalar.

**Gerar uma nova versão do instalador** (desenvolvimento):

```bash
python -m PyInstaller packaging\jarvis.spec --noconfirm --distpath dist --workpath build
```

```bash
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

## Estrutura do código

Cada arquivo tem **uma responsabilidade e no máximo 300 linhas**; o teste `tests/test_structure.py` garante.

| Pasta | O que tem |
|---|---|
| `jarvis/brains/` | Cérebros (Claude, Gemini e NVIDIA) e o roteador com a regra de uso |
| `jarvis/local/` | Modo independente: comandos e pesquisa na web sem IA |
| `jarvis/ui/` | Janela: `api*.py` (ponte com o JavaScript, um assunto por arquivo), `workers.py`, `window.py` e `web/` (HTML, CSS e JS) |
| `jarvis/mcp_tools/` | Ferramentas que o Claude usa, uma por assunto; `jarvis/mcp_server.py` as registra |
| `jarvis/pc/` | Leitura do PC, ações com aprovação, abrir programas e capturar a tela |
| `jarvis/dev/` | Projetos, fila do Claude Code, revisão de mudanças e sessões |
| `jarvis/mail/`, `jarvis/info/`, `jarvis/voice/` | E-mail; clima, notícias e vagas; voz |
| `jarvis/eval/` | Métricas e benchmarks |
| `packaging/` | PyInstaller e Inno Setup |
| `tests/` | Suíte de testes |

## Janela, bandeja e cérebros

- Janela de chat (pywebview) com ícone na bandeja. Fechar a janela só esconde; "Sair" no ícone encerra.
- A conversa guarda as últimas 20 mensagens como contexto.
- Cérebros, em ordem (configurável em `brains`):
  1. **Claude** via `claude -p`, usando a **assinatura** logada no Claude Code. Uma **sessão fica aberta** entre as perguntas (~1,5 s por resposta simples, contra ~11 s abrindo um processo por pergunta) e é aquecida na abertura da Jarvis. Variáveis `ANTHROPIC_*` são removidas antes de chamar o CLI, então nunca é cobrado por API.
  2. **Gemini** (chave gratuita do Google AI Studio).
  3. **NVIDIA NIM** (chave gratuita do build.nvidia.com).
  Se um falhar (limite, rede, sem chave), o próximo responde.

### Chaves do Gemini e da NVIDIA

Crie as chaves nos sites oficiais e guarde-as com o comando abaixo. A chave é digitada sem aparecer na tela e fica no Gerenciador de Credenciais do Windows, nunca em arquivo.

- Gemini: https://aistudio.google.com/apikey
- NVIDIA: https://build.nvidia.com (menu de API keys)

```bash
python -m jarvis --chave gemini
```

```bash
python -m jarvis --chave nvidia
```

## Voz

- Diga **"Hey Jarvis"** (pronúncia em inglês), clique no 🎤 da janela ou use **Falar agora** na bandeja.
- Transcrição **local** com faster-whisper `small` + vocabulário (seu nome, cidade e projetos). Medido com ruído de sala: ~11% de palavras erradas contra ~60% do `base`. Nenhum áudio sai do PC.
- Um **bipe** curto avisa que ela começou a ouvir depois do "Hey Jarvis".
- Resposta falada frase a frase (começa antes de sintetizar tudo) com a voz neural **Francisca** (edge-tts, online e gratuita). Sem internet, usa a voz **Maria** do Windows.
- Código, links e Markdown não são lidos em voz alta; respostas longas são resumidas ("Os detalhes estão na janela").
- **Pausar escuta** na bandeja desliga a palavra de ativação (o 🎤 continua funcionando).
- Configuração em `voz` no `config.json`: `ativa`, `falar_respostas`, `modelo_transcricao`, `voz`, `sensibilidade`.

## Memória, saudação, clima e notícias

- **Ao abrir**, a Jarvis cumprimenta pelo horário, pergunta como você está e diz o clima. Na **primeira abertura do dia** também traz 3 manchetes gerais (G1, BBC Brasil, Agência Brasil) e 3 de tecnologia (Tecnoblog, Canaltech, Olhar Digital), e salva o briefing na memória da Jarvis (nota `Relatórios/...`).
- **Clima** pelo Open-Meteo (grátis, sem chave). Diga "minha cidade é ..." para ela salvar a sua cidade.
- **Memória própria** (sem Obsidian): um único arquivo SQLite, `%APPDATA%\SuperJarvis\memoria.db`, que vai junto da Jarvis (nada para instalar). A Jarvis grava fatos duráveis (uma nota por assunto), o diário, os relatórios, as fichas de projeto, as pesquisas, o caderno de melhorias e o perfil de vagas, e carrega o índice em toda conversa. A busca (`buscar_notas`) ignora acentos e maiúsculas.
  - **Janela "◈ Memória"** (botão no alto): lista, busca, edita, apaga e exporta as notas. O que você editar ou apagar vale na próxima conversa.
  - **Obsidian é opcional.** Na primeira vez que a memória é criada, a Jarvis copia (só lê) as notas de `Jarvis/` do cofre configurado em `obsidian_vault`, sem apagar nada. Para importar de novo: `python -m jarvis --importar-obsidian "C:\caminho\do\cofre"` (só traz o que ainda não existe). Para ver a memória no Obsidian: `python -m jarvis --exportar-memoria "C:\caminho\do\cofre\Jarvis"` ou o botão **Exportar…** (o banco é a fonte da verdade; a cópia sobrescreve notas de mesmo caminho).
  - O caminho do banco pode ser trocado em `memoria_db` no `config.json`. Backup: copie o arquivo `memoria.db`.
  - Mudança de comportamento: a Jarvis não lê mais o resto do seu cofre (só o que foi importado de `Jarvis/`).
- **Lê as suas notas** (somente leitura) para responder sobre seus projetos, por exemplo "o que falta no MeuSistema?".
- **Diário** em `Jarvis/Diário/AAAA-MM-DD.md` com pedidos e ações do dia.
- A Jarvis só escreve dentro da pasta `Jarvis/` do cofre.

## Desempenho do PC

- O Claude consulta ferramentas do PC por um servidor MCP próprio (`python -m jarvis.mcp_server`): visão geral (CPU, RAM, disco, bateria), processos mais pesados, programas de inicialização e uso de disco.
- **Ações só com aprovação:** a IA apenas *propõe* encerrar um processo, limpar temporários ou desativar um programa da inicialização. A proposta aparece como cartão na janela e só é executada quando você clica em **Aprovar**, com nova validação no momento da execução.
- Protegidos: processos essenciais do Windows, a própria Jarvis e a pasta `TEMP\claude` (sessões do Claude Code). Itens de inicialização de todos os usuários exigem administrador e não são alterados.
- Desligar as ferramentas: `"ferramentas_pc": false` no `config.json`.
- As ferramentas do PC funcionam só com o Claude; Gemini e NVIDIA respondem sem elas.

## E-mail (Gmail e Outlook)

- Lê a caixa de entrada do Gmail (API oficial) e do Outlook/Hotmail (Microsoft Graph) com OAuth. Para conectar, siga o guia [docs/CONFIGURAR-EMAIL.md](docs/CONFIGURAR-EMAIL.md).
- Organiza com marcadores (`Jarvis/Financeiro`, `Jarvis: Importante`...) **só após Aprovar**. Nunca apaga, move ou envia.
- Regras fixas no `config.json` + IA para o resto. E-mails que tentam dar ordens à IA viram **Suspeito**.
- Tokens criptografados com DPAPI em `%LOCALAPPDATA%\SuperJarvis\tokens`.

## Vagas de emprego

- Fontes legais e gratuitas: repositórios de vagas da comunidade no GitHub (frontendbr, backend-br, react-brasil) e Remotive (remotas). Cache de 6 h para respeitar os termos da Remotive, que pede no máximo cerca de 4 consultas por dia, link para a vaga e a fonte citada. LinkedIn e outros sites que proíbem robôs não são usados.
- **Perfil** na nota `Perfil Profissional` da memória (criada vazia no primeiro uso): stack, nível, modalidade, cidade, o que evitar e inglês. Edite na janela **Memória** ou diga, por exemplo, "Jarvis, minha stack é Python e React".
- Cada vaga recebe uma **nota de 0 a 100 com os motivos** (stack, nível, remota ou na sua cidade, idioma, recência). Vagas já mostradas não se repetem no briefing.
- O briefing do dia traz até 3 vagas novas. Os links abrem no navegador padrão.
- **A Jarvis nunca se candidata**: ela só mostra a vaga.

## Parceira de desenvolvimento

- Cadastre projetos por voz ou texto: "Jarvis, meu projeto MeuApp fica em C:\...\pasta". Eles ficam em `projetos` no `config.json`.
- **Ficha do projeto**: conte à Jarvis o que é o projeto, a stack, objetivos, decisões e pendências ("Jarvis, anota no MeuApp que decidimos usar Postgres"). Ela grava na nota `Projetos/<projeto>/Sobre` da memória (Descrição substitui; as outras seções acumulam com data; você pode editar a nota na janela **Memória**) e manda essa ficha como contexto em toda análise, plano ou execução do Claude Code.
- **Projeto novo**: "Jarvis, cria um projeto Loja Virtual em C:\...\Projetos". Aparece um cartão; só depois que você aprova ela cria a pasta com `README.md`, roda `git init` (sem commit), cadastra o projeto e abre a ficha. Ela nunca usa uma pasta que já existe. Depois, peça para o Claude Code montar a estrutura (cartão de execução).
- **Esquecer projeto**: tira da lista da Jarvis, sem apagar pasta nem ficha.
- **Estado rápido** (sem IA): branch, arquivos alterados e últimos commits.
- **Analisar** e **planejar**: o Claude Code lê o projeto (somente Read/Glob/Grep, modo `dontAsk`) e responde ou monta um plano com arquivos, passos, riscos e testes.
- **Executar**: o Claude Code pode editar arquivos **só depois que você aprova o cartão**, só em projetos git, sem commit/push e sem Bash irrestrito (apenas `git status`/`git diff`). Ao final, você recebe o `git diff --stat` para revisar.
- As tarefas rodam em segundo plano na janela, uma por vez. Ao terminar, a Jarvis avisa em texto e voz e salva o resultado na memória (notas `Projetos/<projeto>/...`).
- Tudo usa a sua assinatura do Claude (sem chave de API), então conta nos limites do plano Pro.
- **Dashboards de documentos**: clique em 📊 na janela e escolha um arquivo, ou diga "Jarvis, cria um dashboard de C:\...\vendas.xlsx". O painel do **Dashboard Universal** (versão 0.7.1) está **dentro da Jarvis**, em `jarvis/dashboard/painel.html`: não precisa do programa instalado. A Jarvis embute o documento nesse painel e abre no navegador. Aceita CSV, TSV, XLSX, DOCX, PDF (tabelas), JSON, GeoJSON, KML e KMZ, até 50 MB (o `.doc` antigo não). Para atualizar o painel, troque `painel.html` pelo `dist/index.html` de uma versão nova. Tudo roda no PC; o documento não é alterado nem enviado. Os HTMLs ficam em `%LOCALAPPDATA%\SuperJarvis\dashboards`.
- **Monitor de sessões**: a cada 5 s a Jarvis olha as sessões do Claude Code abertas no PC (terminal ou app) e avisa uma vez, em texto e voz, quando uma passa a esperar você: pedido de permissão, pergunta ou turno encerrado. Pergunte "alguma sessão está me esperando?" (ferramenta `sessoes_claude_code`). Só lê `~/.claude/sessions/*.json` e o fim dos `~/.claude/projects/*/*.jsonl`, nunca escreve neles. O formato não é oficial: o que foi confirmado e o que é estimativa está em `jarvis/dev/sessions.py`. Avisos com "talvez" são estimativa (no app desktop, uma ferramenta parada há mais de 60 s pode ser pedido de permissão ou só um comando demorado). Ao abrir a Jarvis, sessões que já estavam só paradas não são anunciadas.

> **Sobre o painel do dashboard:** o arquivo `jarvis/dashboard/painel.html` é um *build* gerado (4 MB, com bibliotecas de terceiros)
> do projeto Dashboard Universal e **não fica no Git**. Sem ele, o recurso avisa que o painel não foi encontrado e o resto da
> Jarvis funciona normalmente. Para ativar, copie o `dist/index.html` gerado pelo `npm run build` do Dashboard Universal para esse caminho.

## Programação: linguagens, lógica, sistemas e evolução

A Jarvis tem uma base própria de conhecimento de programação, **curada à mão, offline e sem IA**. Ela funciona nos dois modos (com ou sem IA). Com o Claude ligado, as mesmas ferramentas (MCP) servem de guia para o Claude Code. **Limite honesto:** isto não é conhecimento ilimitado. Ela resolve com certeza o que está na base e ensina o método para o resto; sistemas sob medida, além dos modelos prontos, continuam sendo feitos pelo Claude Code (a Jarvis propõe e você aprova).

**1. Tecnologias** (`jarvis/dev/conhecimento/`): 42 linguagens, frameworks, bancos e stacks de **front end, back end, full stack e mobile** (JavaScript, TypeScript, Python, Java, C#, PHP, Go, SQL, React, Vue, Angular, Next.js, Node, Express, FastAPI, Django, Spring, Laravel, PostgreSQL, MongoDB, MERN...). Para cada uma: o que é, usos, pontos fortes e fracos, quando escolher e como começar.
- "o que é React?", "compare Django e FastAPI", "Python ou Node?", "quais linguagens para back end?"
- "qual stack para uma loja virtual?": recomenda front, back e banco para 9 tipos de sistema, com o porquê e alternativas.

**2. Sistemas prontos para rodar** (`jarvis/dev/modelos/`): "crie um sistema chamado Loja com FastAPI e React em C:\Projetos". Combinações de back-end **FastAPI** ou **Express** com front-end **React (Vite)** ou **HTML/CSS/JS**, ou cada peça sozinha. Cada projeto traz exemplo de CRUD com testes, README (instalar, rodar, testar) e `.gitignore`.
- **Só depois do seu "Aprovar" no cartão**: a Jarvis só propõe. Nunca usa uma pasta que já existe, faz `git init` sem commit e anota a stack na ficha do projeto.
- Os quatro modelos foram **executados de verdade** na criação: `pytest` do FastAPI, `node --test` do Express, verificação do JavaScript do front HTML e `vite build` do React.

**3. Lógica de programação** (`jarvis/dev/logica/`): 28 conceitos (variáveis, condicionais, laços, funções, recursão, listas, dicionários, pilha, fila, árvores, grafos, ordenação, busca, Big-O, POO, testes, depuração, banco de dados, APIs, git, segurança, arquitetura...) e **15 algoritmos clássicos** (fatorial, Fibonacci, primo, MDC, palíndromo, inverter, maior elemento, média, busca linear e binária, bolha, quicksort, contar palavras, FizzBuzz, decimal→binário) com ideia, pseudocódigo, complexidade e código em **Python, JavaScript, Go, Java e C#**.
- "explique recursão", "qual a diferença entre pilha e fila", "busca binária em Java", "como resolver um problema de programação?" (roteiro de 9 passos).
- Python, JavaScript e Go são **executados nos testes** contra casos de entrada e saída. Java e C# seguem a mesma lógica, mas **não são compilados aqui** (a resposta avisa).

**3b. Engenharia, arquitetura, sistemas e UI/UX** (`jarvis/dev/engenharia/`, `jarvis/dev/ux/`, `jarvis/dev/saber.py`): 29 tópicos (engenharia de software, requisitos, ágil, revisão de código, dívida técnica, DevOps, observabilidade, segurança OWASP, camadas, hexagonal, microsserviços, eventos, DDD, SOLID, APIs, escalabilidade, cache, sistemas distribuídos, contêineres, 12-factor) e 14 de UX (Nielsen, hierarquia, tipografia, cor, WCAG, formulários, estados, microcopy, responsividade, navegação, design system, pesquisa, animação), **8 padrões de projeto** com código testado em Python e JavaScript, ferramentas de design (contraste WCAG, paleta, escala tipográfica, tokens CSS) e geradores de texto (tabela SQL, ADR, história de usuário, OpenAPI, CI, Dockerfile, .editorconfig). Perguntas: "explique SOLID", "mostre o padrão Observer em JavaScript", "contraste #767676 sobre #ffffff", "crie uma tabela clientes com nome texto, idade inteiro". Ferramentas MCP: `explicar_topico_de_engenharia`, `listar_o_que_a_jarvis_sabe`, `avaliar_contraste`, `gerar_tokens_de_design`, `gerar_artefato`. A avaliação de projetos ganhou checagens de arquitetura (ciclos de importação) e de CSS.

**4. Habilidades que evoluem** (`jarvis/dev/habilidades/`): 23 habilidades de um bom programador (lógica, linguagens, estruturas, testes, depuração, código limpo, segurança, bancos, APIs, arquitetura, versionamento, automação, desempenho, logs, acessibilidade, documentação, organização, aprendizado contínuo), cada uma com três níveis, práticas, o que estudar e um treino.
- **"avalie o projeto X"** (ou "avalie o seu código", ou `avalie C:\pasta`): avalia, **só lendo**, 9 aspectos (testes, documentação, versionamento, segurança, código limpo, automação, logs, acessibilidade, organização), dá nota de 0 a 100 por aspecto, mostra o que achou e o que melhorar, e **compara com a avaliação anterior** para mostrar a evolução. O histórico fica na memória (`Habilidades/Avaliações/<projeto>`). São heurísticas, não um veredito.
- **Evolução da própria Jarvis**: ao avaliar o código dela, as melhorias entram no **caderno de melhorias**; "Jarvis, melhore-se" propõe a próxima (com seu aprovo e a verificação por testes). Depois, avaliar de novo mostra se a nota subiu.
- **"o que devo estudar?"** indica a habilidade mais fraca da última avaliação; quando tudo que dá para medir está ótimo, passa a sugerir as que não se medem, em rodízio. **"treino da semana"** dá uma habilidade por semana, nas 23. Também: "checklist de segurança", "plano de evolução em testes", "quais habilidades de programador?".

Ferramentas MCP para o Claude: `consultar_tecnologia`, `listar_tecnologias`, `comparar_tecnologias`, `recomendar_stack`, `modelos_de_projeto`, `propor_criar_projeto(modelo=...)`, `explicar_conceito`, `exemplo_de_algoritmo`, `como_resolver_problema`, `listar_conceitos_e_algoritmos`, `habilidades_de_programador`, `avaliar_projeto`, `proxima_habilidade`, `treino_da_semana`, `checklist_de_revisao` e `plano_de_evolucao`.

## Anexos (ler, analisar e criar arquivos)

- Clique no **clipe** ou **arraste arquivos** para a janela: texto e código, PDF, Word (.docx), Excel (.xlsx) e imagens (até 25 MB).
- A Jarvis lê cada anexo pela ferramenta `ler_anexo`. As imagens são **vistas** pelo Claude, o que serve para prints de erro, telas e diagramas.
- Para criar ou melhorar algo, ela salva o resultado com `salvar_arquivo` em `Documentos\Jarvis`, **sem nunca sobrescrever** (cria "nome (2)").
- As cópias dos anexos ficam em `%LOCALAPPDATA%\SuperJarvisnexos` por 30 dias. O arquivo original não é alterado.

## Pesquisa na internet e criação de documentos

- **Pesquisa em níveis** (pela sua assinatura do Claude, sem custo extra):

  | Nível | Sites | Onde roda |
  |---|---|---|
  | **simples** | ~3 | Na própria conversa, em segundos |
  | **média** | ~15 | Em segundo plano, alguns minutos |
  | **difícil** | ~35 | Em segundo plano |
  | **extra difícil** | 50 ou mais | Em segundo plano, gasta bastante do limite |

  - A Jarvis escolhe o nível sozinha, ou use o que você pedir ("Jarvis, pesquisa difícil sobre...").
  - O relatório traz a resposta direta, as categorias, as opções com prós e contras, as divergências entre as fontes e a lista de fontes. Ele é salvo na memória da Jarvis (notas `Pesquisas/...`).
  - As pesquisas em segundo plano rodam isoladas: só buscam e leem sites, sem acesso às ferramentas do PC.
  - Medido: uma pesquisa média citou 31 sites em 2,7 min.
- **Criar documentos** em `Documentos\Jarvis`, sem sobrescrever:
  - **Word** e **PDF**, a partir de Markdown (títulos, listas, tabelas, negrito);
  - **Excel**, com números e fórmulas;
  - **PowerPoint**, com capa, tópicos e notas.

## Abrir coisas, revisar mudanças, olhar a tela e cérebros

- **Abrir por voz ou texto**: programas do Menu Iniciar (WhatsApp, VS Code, Obsidian, calculadora...), sites (só `http(s)`), pastas (Documentos, Downloads, Área de Trabalho...) e projetos cadastrados (VS Code e, se você pedir, o Terminal).
- **Revisão das mudanças do Claude Code**: depois de uma execução aprovada, aparece um cartão com os arquivos e o diff colorido e os botões **Manter** e **Desfazer**. O Desfazer devolve cada arquivo ao estado de antes da execução, **inclusive as suas alterações que ainda não estavam em commit**.
- **"Olha minha tela"**: a Jarvis tira um print de todos os monitores, sem a própria janela, e o Claude analisa. Só é usado quando você pede.
- **⚙ Cérebros**: cadastre a chave grátis do Gemini (ou da NVIDIA). A Jarvis testa a chave antes de guardar, no cofre do Windows, e escolhe sozinha o modelo Flash disponível.
  - **Só como reserva**: o Gemini entra quando o limite do Claude acaba.
  - **Perguntas simples**: conversa rápida vai para o Gemini e economiza o limite do Claude. Tudo que usa ferramentas continua no Claude.
  - Em qualquer modo, diga **"Gemini, ..."** ou **"pergunte ao Gemini ..."**.

## Modo independente (sem IA)

A Jarvis **não para quando o limite do Claude acaba**. Um motor próprio, sem IA generativa, fica sempre como o último cérebro.

**Só a inteligência da Jarvis (sem nenhuma IA).** No painel **⚙ Cérebros**, marque "Só a inteligência da Jarvis (sem nenhuma IA)": a partir do próximo pedido nada chama Claude, Gemini ou NVIDIA, não abre a sessão do Claude (poupa RAM) e não precisa de chave, assinatura nem limite. Desmarque e eles voltam a ajudar. (No `config.json`: `somente_independente`.) Além dos comandos abaixo, o motor próprio entende:
- **memória**: "lembre que eu prefiro vagas remotas", "o que você sabe sobre mim?", "busque na memória sobre ...";
- **perfil e projetos**: "meu nível é pleno", "minha stack é Python e React", "minha cidade é Fortaleza", "quero evitar PHP", "meus projetos", "anota no projeto Loja que decidimos usar Postgres", "ficha do projeto Loja";
- **dashboards**: "crie um dashboard de C:\pasta\vendas.xlsx";
- **sessões do Claude Code**: "alguma sessão está me esperando?".
- **programação**: consultar, comparar e recomendar tecnologias, criar sistemas prontos, explicar lógica e algoritmos e avaliar projetos (seção "Programação" acima).

Sem IA ela não conversa livremente, não escreve textos novos, não classifica e-mails, não analisa imagens nem executa tarefas de código (isso continua com o Claude). O reconhecimento de voz ("Hey Jarvis" e transcrição) usa modelos pequenos que rodam no seu PC, sem API; não é o "cérebro".

- **Comandos diretos** são atendidos na hora, sem gastar limite de nenhuma IA: abrir programas, sites, pastas e projetos; estado do PC e programas pesados; clima; notícias; vagas; hora e data.
- **Pesquisa na internet sem IA** usando fontes oficiais:
  - a Wikipedia (pt/en), com checagem de relevância;
  - a API oficial do DuckDuckGo;
  - opcionalmente, a **Brave Search API**, um buscador (não é IA), gratuito até cerca de 2.000 buscas por mês, cadastrado no painel ⚙.

  A resposta é um **resumo extrativo**: só frases que estão nos sites, cada uma com a fonte [n]. Nada é inventado.
- **Respeito aos sites:** User-Agent identificado, cache de 1 dia e intervalo entre pedidos. Não raspa buscadores nem contorna a verificação anti-robô.
- **Limites honestos:** sem IA, ela não conversa livremente, não escreve textos novos e não analisa imagens. Para isso continuam o Claude, o Gemini e a NVIDIA.

## Avaliação de qualidade (métricas e benchmarks)

```bash
python -m jarvis.eval
```

```bash
python -m jarvis.eval --ias claude,local --juiz gemini
```

O primeiro roda os benchmarks sem gastar IA. O segundo também avalia as respostas dos cérebros (gasta limite). O relatório fica na memória da Jarvis (nota `Avaliações/...`).

- **Métricas:**
  - **BLEU** (tradução) e **ROUGE-1/2/L** (sumarização, com precisão, recall e F1).
  - **METEOR**, com radicais em português; sem o dicionário de sinônimos do WordNet, que só existe em inglês.
  - **BERTScore**, com o MiniLM multilíngue de 112 MB. Os valores não são comparáveis aos publicados com o RoBERTa-large.
  - **Precisão, recall e F1** por intenção (macro e micro) e matriz de confusão.
- **BLEURT** não roda neste PC (TensorFlow e modelo de 2 GB ou mais). O substituto é o **juiz por rubrica** (`--juiz`), de preferência um cérebro diferente do avaliado, para não favorecer a si mesmo.
- **Critérios em toda resposta**, de 0 a 10, mostrados na janela (passe o mouse sobre "qualidade"): coerência, clareza, relevância, fidelidade (quando há fontes) e fluidez. São heurísticas de **forma**: não dizem se a resposta está correta.
- **Benchmarks:**
  - comandos com conjunto de **ajuste** e de **validação** separados; o relatório aponta overfitting quando a diferença passa de 5%;
  - **robustez** (sem acentos, maiúsculas, erro de digitação, "por favor", ruído);
  - resumos contra o baseline **Lead-2**;
  - respostas por cérebro, com latência.
- **Resultados de 15/10/2026:**
  - comandos: 100% no ajuste e **94,7% na validação**;
  - robustez: 93,5% com erro de digitação;
  - resumo extrativo: ROUGE-L 0,35, **abaixo** do Lead-2 (0,43);
  - Claude: BERTScore 0,91 e juiz 9,7/10.

## Autoaperfeiçoamento

- **Caderno de melhorias** na nota `Melhorias` da memória: um checklist que você também edita na janela **Memória**. Ideias entram sozinhas quando um pedido não é entendido, quando uma resposta tira nota baixa ou quando nenhum cérebro responde. Também dá para dizer "anota uma melhoria: ...".
- **"Jarvis, melhore-se"**: o Claude Code altera o código da própria Jarvis para implementar **uma** melhoria, só depois que você aprova o cartão. Vale para a cópia de desenvolvimento; a versão instalada não altera o próprio código.
- Depois de **Manter**, a Jarvis roda sozinha os **testes e o benchmark** e compara com a última versão aprovada. Se algo piorar, oferece **Desfazer mudanças**; se estiver tudo certo, oferece **Reiniciar agora**.
- Em todos os casos a melhoria passa pela revisão do diff, e a Jarvis nunca faz commit sozinha.

## Onde ficam as coisas

| O quê | Onde |
|---|---|
| Configuração | `%APPDATA%\SuperJarvis\config.json` (criada na primeira execução) |
| Logs | `%LOCALAPPDATA%\SuperJarvis\logs\jarvis.log` |
| Pasta de trabalho do Claude | `%LOCALAPPDATA%\SuperJarvis\claude-workspace` (vazia, evita carregar configurações de outros projetos) |

## Testes

```bash
python -m pytest
```
