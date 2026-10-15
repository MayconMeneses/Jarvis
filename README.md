# Super Jarvis

Assistente pessoal para Windows. O plano completo está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

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
- **Estado rápido** (sem IA): branch, arquivos alterados e últimos commits.
- **Analisar** e **planejar**: o Claude Code lê o projeto (somente Read/Glob/Grep, modo `dontAsk`) e responde ou monta um plano com arquivos, passos, riscos e testes.
- **Executar**: o Claude Code pode editar arquivos **só depois que você aprova o cartão**, só em projetos git, sem commit/push e sem Bash irrestrito (apenas `git status`/`git diff`). Ao final, você recebe o `git diff --stat` para revisar.
- As tarefas rodam em segundo plano na janela, uma por vez. Ao terminar, a Jarvis avisa em texto e voz e salva o resultado em `Jarvis/Projetos/<projeto>/` no Obsidian.
- Tudo usa a sua assinatura do Claude (sem chave de API), então conta nos limites do plano Pro.
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
