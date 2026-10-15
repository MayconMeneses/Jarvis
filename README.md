# Super Jarvis

Assistente pessoal para Windows. O plano completo está em [PLANO-SUPER-JARVIS.md](PLANO-SUPER-JARVIS.md).

## Estado atual: Fase 0 (fundação)

- Conversa por texto no terminal.
- Cérebro: Claude via `claude -p`, usando a **assinatura** logada no Claude Code. Variáveis `ANTHROPIC_*` são removidas antes de chamar o CLI, então nunca é cobrado por API.
- Roteador de cérebros pronto para receber Gemini e NVIDIA NIM (Fase 1).

## Rodar

Requisitos: Python 3.11 e o Claude Code instalado e logado (`claude auth status`).

```bash
python -m venv C:\Users\maico\.venvs\super-jarvis
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m pip install -e ".[dev]"
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis "Olá, Jarvis"
```

Sem argumentos, `python -m jarvis` abre uma conversa contínua (digite `sair` para encerrar).

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
