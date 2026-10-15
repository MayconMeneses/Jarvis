# Super Jarvis

Assistente pessoal para Windows. O plano completo está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

## Estado atual: Fase 2 (desempenho do PC)

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
