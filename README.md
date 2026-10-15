# Super Jarvis

Assistente pessoal para Windows. O plano completo está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

## Modo independente (sem IA)

A Jarvis **não para quando o limite do Claude acaba**. Um motor próprio, sem IA generativa, fica sempre como o último cérebro.

- **Comandos diretos** são atendidos na hora, sem gastar limite de nenhuma IA: abrir programas, sites, pastas e projetos; estado do PC e programas pesados; clima; notícias; vagas; hora e data.
- **Pesquisa na internet sem IA** usando fontes oficiais:
  - a Wikipedia (pt/en), com checagem de relevância;
  - a API oficial do DuckDuckGo;
  - opcionalmente, a **Brave Search API**, um buscador (não é IA), gratuito até cerca de 2.000 buscas por mês, cadastrado no painel ⚙.

  A resposta é um **resumo extrativo**: só frases que estão nos sites, cada uma com a fonte [n]. Nada é inventado.
- **Respeito aos sites:** User-Agent identificado, cache de 1 dia e intervalo entre pedidos. Não raspa buscadores nem contorna a verificação anti-robô.
- **Limites honestos:** sem IA, ela não conversa livremente, não escreve textos novos e não analisa imagens. Para isso continuam o Claude, o Gemini e a NVIDIA.

## Abrir coisas, revisar mudanças, olhar a tela e cérebros

- **Abrir por voz ou texto**: programas do Menu Iniciar (WhatsApp, VS Code, Obsidian, calculadora...), sites (só `http(s)`), pastas (Documentos, Downloads, Área de Trabalho...) e projetos cadastrados (VS Code e, se você pedir, o Terminal).
- **Revisão das mudanças do Claude Code**: depois de uma execução aprovada, aparece um cartão com os arquivos e o diff colorido e os botões **Manter** e **Desfazer**. O Desfazer devolve cada arquivo ao estado de antes da execução, **inclusive as suas alterações que ainda não estavam em commit**.
- **"Olha minha tela"**: a Jarvis tira um print de todos os monitores, sem a própria janela, e o Claude analisa. Só é usado quando você pede.
- **⚙ Cérebros**: cadastre a chave grátis do Gemini (ou da NVIDIA). A Jarvis testa a chave antes de guardar, no cofre do Windows, e escolhe sozinha o modelo Flash disponível.
  - **Só como reserva**: o Gemini entra quando o limite do Claude acaba.
  - **Perguntas simples**: conversa rápida vai para o Gemini e economiza o limite do Claude. Tudo que usa ferramentas continua no Claude.
  - Em qualquer modo, diga **"Gemini, ..."** ou **"pergunte ao Gemini ..."**.

## Pesquisa na internet e criação de documentos

- **Pesquisa em níveis** (pela sua assinatura do Claude, sem custo extra):

  | Nível | Sites | Onde roda |
  |---|---|---|
  | **simples** | ~3 | Na própria conversa, em segundos |
  | **média** | ~15 | Em segundo plano, alguns minutos |
  | **difícil** | ~35 | Em segundo plano |
  | **extra difícil** | 50 ou mais | Em segundo plano, gasta bastante do limite |

  - A Jarvis escolhe o nível sozinha, ou use o que você pedir ("Jarvis, pesquisa difícil sobre...").
  - O relatório traz a resposta direta, as categorias, as opções com prós e contras, as divergências entre as fontes e a lista de fontes. Ele é salvo em `Jarvis/Pesquisas` no Obsidian.
  - As pesquisas em segundo plano rodam isoladas: só buscam e leem sites, sem acesso às ferramentas do PC.
  - Medido: uma pesquisa média citou 31 sites em 2,7 min.
- **Criar documentos** em `Documentos\Jarvis`, sem sobrescrever:
  - **Word** e **PDF**, a partir de Markdown (títulos, listas, tabelas, negrito);
  - **Excel**, com números e fórmulas;
  - **PowerPoint**, com capa, tópicos e notas.

## Anexos (ler, analisar e criar arquivos)

- Clique no **clipe** ou **arraste arquivos** para a janela: texto e código, PDF, Word (.docx), Excel (.xlsx) e imagens (até 25 MB).
- A Jarvis lê cada anexo pela ferramenta `ler_anexo`. As imagens são **vistas** pelo Claude, o que serve para prints de erro, telas e diagramas.
- Para criar ou melhorar algo, ela salva o resultado com `salvar_arquivo` em `Documentos\Jarvis`, **sem nunca sobrescrever** (cria "nome (2)").
- As cópias dos anexos ficam em `%LOCALAPPDATA%\SuperJarvisnexos` por 30 dias. O arquivo original não é alterado.

## Estado atual: Fase 8 (instalador)

**Instalar:** rode `dist\SuperJarvis-Setup-0.8.0.exe` (131 MB).
- Instala só para o seu usuário, em `%LOCALAPPDATA%\Programs\SuperJarvis`, sem pedir administrador.
- Cria atalho no menu Iniciar. O atalho na área de trabalho e o "Abrir a Jarvis quando o Windows iniciar" são opcionais.
- Avisa se o Claude Code não estiver instalado.
- Desinstale em Configurações > Aplicativos. Suas configurações, chaves e notas no Obsidian **são mantidas**.
- Só uma Jarvis abre por vez. Abrir de novo apenas avisa que ela já está na bandeja.

Dois executáveis na pasta do programa:
- `Jarvis.exe`: janela, bandeja e voz.
- `jarvis-cli.exe`: terminal. Use `jarvis-cli.exe --conectar gmail` e `jarvis-cli.exe --chave gemini` no lugar de `python -m jarvis ...`. Também é o servidor MCP usado pelo Claude.

**Gerar uma nova versão do instalador** (desenvolvimento):

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m PyInstaller packaging\jarvis.spec --noconfirm --distpath dist --workpath build
```

```bash
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" packaging\installer.iss
```

## Fase 7 (parceira de desenvolvimento)

- Cadastre projetos por voz ou texto: "Jarvis, meu projeto Comandiva fica em C:\...\pasta". Eles ficam em `projetos` no `config.json`.
- **Ficha do projeto**: conte à Jarvis o que é o projeto, a stack, objetivos, decisões e pendências ("Jarvis, anota no Comandiva que decidimos usar Postgres"). Ela grava em `Jarvis/Projetos/<projeto>/Sobre.md` no Obsidian (Descrição substitui; as outras seções acumulam com data; suas edições na nota são mantidas) e manda essa ficha como contexto em toda análise, plano ou execução do Claude Code.
- **Projeto novo**: "Jarvis, cria um projeto Loja Virtual em C:\...\Projetos". Aparece um cartão; só depois que você aprova ela cria a pasta com `README.md`, roda `git init` (sem commit), cadastra o projeto e abre a ficha. Ela nunca usa uma pasta que já existe. Depois, peça para o Claude Code montar a estrutura (cartão de execução).
- **Esquecer projeto**: tira da lista da Jarvis, sem apagar pasta nem ficha.
- **Estado rápido** (sem IA): branch, arquivos alterados e últimos commits.
- **Analisar** e **planejar**: o Claude Code lê o projeto (somente Read/Glob/Grep, modo `dontAsk`) e responde ou monta um plano com arquivos, passos, riscos e testes.
- **Executar**: o Claude Code pode editar arquivos **só depois que você aprova o cartão**, só em projetos git, sem commit/push e sem Bash irrestrito (apenas `git status`/`git diff`). Ao final, você recebe o `git diff --stat` para revisar.
- As tarefas rodam em segundo plano na janela, uma por vez. Ao terminar, a Jarvis avisa em texto e voz e salva o resultado em `Jarvis/Projetos/<projeto>/` no Obsidian.
- Tudo usa a sua assinatura do Claude (sem chave de API), então conta nos limites do plano Pro.
- **Dashboards de documentos**: clique em 📊 na janela e escolha um arquivo, ou diga "Jarvis, cria um dashboard de C:\...\vendas.xlsx". O painel do **Dashboard Universal** (versão 0.7.1) está **dentro da Jarvis**, em `jarvis/dashboard/painel.html`: não precisa do programa instalado. A Jarvis embute o documento nesse painel e abre no navegador. Aceita CSV, TSV, XLSX, DOCX, PDF (tabelas), JSON, GeoJSON, KML e KMZ, até 50 MB (o `.doc` antigo não). Para atualizar o painel, troque `painel.html` pelo `dist/index.html` de uma versão nova. Tudo roda no PC; o documento não é alterado nem enviado. Os HTMLs ficam em `%LOCALAPPDATA%\SuperJarvis\dashboards`.
- **Monitor de sessões**: a cada 5 s a Jarvis olha as sessões do Claude Code abertas no PC (terminal ou app) e avisa uma vez, em texto e voz, quando uma passa a esperar você: pedido de permissão, pergunta ou turno encerrado. Pergunte "alguma sessão está me esperando?" (ferramenta `sessoes_claude_code`). Só lê `~/.claude/sessions/*.json` e o fim dos `~/.claude/projects/*/*.jsonl`, nunca escreve neles. O formato não é oficial: o que foi confirmado e o que é estimativa está em `jarvis/dev/sessions.py`. Avisos com "talvez" são estimativa (no app desktop, uma ferramenta parada há mais de 60 s pode ser pedido de permissão ou só um comando demorado). Ao abrir a Jarvis, sessões que já estavam só paradas não são anunciadas.

## Fase 6 (vagas de emprego)

- Fontes legais e gratuitas: repositórios de vagas da comunidade no GitHub (frontendbr, backend-br, react-brasil) e Remotive (remotas). Cache de 6 h para respeitar os termos da Remotive, que pede no máximo cerca de 4 consultas por dia, link para a vaga e a fonte citada. LinkedIn e outros sites que proíbem robôs não são usados.
- **Perfil** em `Jarvis/Perfil Profissional.md` no Obsidian (criado vazio no primeiro uso): stack, nível, modalidade, cidade, o que evitar e inglês. Preencha no Obsidian ou diga, por exemplo, "Jarvis, minha stack é Python e React".
- Cada vaga recebe uma **nota de 0 a 100 com os motivos** (stack, nível, remota ou na sua cidade, idioma, recência). Vagas já mostradas não se repetem no briefing.
- O briefing do dia traz até 3 vagas novas. Os links abrem no navegador padrão.
- **A Jarvis nunca se candidata**: ela só mostra a vaga.

## Fase 5 (memória, saudação, clima e notícias)

- **Ao abrir**, a Jarvis cumprimenta pelo horário, pergunta como você está e diz o clima. Na **primeira abertura do dia** também traz 3 manchetes gerais (G1, BBC Brasil, Agência Brasil) e 3 de tecnologia (Tecnoblog, Canaltech, Olhar Digital), e salva o briefing em `Jarvis/Relatórios` no Obsidian.
- **Clima** pelo Open-Meteo (grátis, sem chave). Diga "minha cidade é ..." para ela salvar a sua cidade.
- **Memória no Obsidian** (`obsidian_vault` no `config.json`): a Jarvis grava fatos duráveis em `Jarvis/Memória` (uma nota por assunto) e as carrega em toda conversa. Editou ou apagou uma nota, ela passa a usar a versão nova.
- **Lê as suas notas** (somente leitura) para responder sobre seus projetos, por exemplo "o que falta no MM System?".
- **Diário** em `Jarvis/Diário/AAAA-MM-DD.md` com pedidos e ações do dia.
- A Jarvis só escreve dentro da pasta `Jarvis/` do cofre.

## Fase 4 (voz)

- Diga **"Hey Jarvis"** (pronúncia em inglês), clique no 🎤 da janela ou use **Falar agora** na bandeja.
- Transcrição **local** com faster-whisper `small` + vocabulário (seu nome, cidade e projetos). Medido com ruído de sala: ~11% de palavras erradas contra ~60% do `base`. Nenhum áudio sai do PC.
- Um **bipe** curto avisa que ela começou a ouvir depois do "Hey Jarvis".
- Resposta falada frase a frase (começa antes de sintetizar tudo) com a voz neural **Francisca** (edge-tts, online e gratuita). Sem internet, usa a voz **Maria** do Windows.
- Código, links e Markdown não são lidos em voz alta; respostas longas são resumidas ("Os detalhes estão na janela").
- **Pausar escuta** na bandeja desliga a palavra de ativação (o 🎤 continua funcionando).
- Configuração em `voz` no `config.json`: `ativa`, `falar_respostas`, `modelo_transcricao`, `voz`, `sensibilidade`.

## Fase 3 (e-mail Gmail e Outlook)

- Lê a caixa de entrada do Gmail (API oficial) e do Outlook/Hotmail (Microsoft Graph) com OAuth. Para conectar, siga o guia [docs/CONFIGURAR-EMAIL.md](docs/CONFIGURAR-EMAIL.md).
- Organiza com marcadores (`Jarvis/Financeiro`, `Jarvis: Importante`...) **só após Aprovar**. Nunca apaga, move ou envia.
- Regras fixas no `config.json` + IA para o resto. E-mails que tentam dar ordens à IA viram **Suspeito**.
- Tokens criptografados com DPAPI em `%LOCALAPPDATA%\SuperJarvis\tokens`.

## Fase 2 (desempenho do PC)

- O Claude consulta ferramentas do PC por um servidor MCP próprio (`python -m jarvis.mcp_server`): visão geral (CPU, RAM, disco, bateria), processos mais pesados, programas de inicialização e uso de disco.
- **Ações só com aprovação:** a IA apenas *propõe* encerrar um processo, limpar temporários ou desativar um programa da inicialização. A proposta aparece como cartão na janela e só é executada quando você clica em **Aprovar**, com nova validação no momento da execução.
- Protegidos: processos essenciais do Windows, a própria Jarvis e a pasta `TEMP\claude` (sessões do Claude Code). Itens de inicialização de todos os usuários exigem administrador e não são alterados.
- Desligar as ferramentas: `"ferramentas_pc": false` no `config.json`.
- As ferramentas do PC funcionam só com o Claude; Gemini e NVIDIA respondem sem elas.

## Fase 1 (janela, bandeja e roteador)

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
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis --chave gemini
```

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis --chave nvidia
```

## Rodar

Requisitos: Python 3.11 e o Claude Code instalado e logado (`claude auth status`).

```bash
python -m venv C:\Users\maico\.venvs\super-jarvis
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m pip install -e ".[dev]"
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis "Olá, Jarvis"
```

- `python -m jarvis` abre a janela (use `pythonw.exe` para não abrir o console).
- `python -m jarvis --texto` conversa no terminal (digite `sair` para encerrar).
- `python -m jarvis "pergunta"` responde uma vez no terminal.

## Onde ficam as coisas

| O quê | Onde |
|---|---|
| Configuração | `%APPDATA%\SuperJarvis\config.json` (criada na primeira execução) |
| Logs | `%LOCALAPPDATA%\SuperJarvis\logs\jarvis.log` |
| Pasta de trabalho do Claude | `%LOCALAPPDATA%\SuperJarvis\claude-workspace` (vazia, evita carregar configurações de outros projetos) |

## Testes

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m pytest
```
