# Super Jarvis

Assistente pessoal para Windows. O plano completo está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

## Estado atual: Fase 7 (parceira de desenvolvimento)

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
- Transcrição **local** com faster-whisper (`base` por padrão; `small` acerta mais, mas é cerca de 3 vezes mais lento e pesado). Nenhum áudio sai do PC.
- Resposta falada com a voz neural **Francisca** (edge-tts, online e gratuita). Sem internet, usa a voz **Maria** do Windows.
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
  1. **Claude** via `claude -p`, usando a **assinatura** logada no Claude Code. Variáveis `ANTHROPIC_*` são removidas antes de chamar o CLI, então nunca é cobrado por API.
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
