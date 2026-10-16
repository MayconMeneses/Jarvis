# Análise dos 6 repositórios "Jarvis" enviados

Data: 15/10/2026. Clones em `_referencias/` (somente para estudo). O foco da análise foi o que serve para **uso pessoal no dia a dia e para programar**.

| Repositório | ⭐ | Licença | O que é de verdade | Vale para a Super Jarvis? |
|---|---|---|---|---|
| [ctaylo21/jarvis](https://github.com/ctaylo21/jarvis) | 726 | MIT | **Não é assistente**: configuração de Neovim + tmux + zsh (abrir arquivos por busca aproximada, buscar no projeto, uma sessão por projeto) | Sim, como **ideia**: comando "abrir projeto" |
| [danilofalcao/jarvis](https://github.com/danilofalcao/jarvis) | 650 | MIT | Assistente de código web (Flask): vários modelos, anexos (PDF, Word, Excel, OCR), workspaces, **prévia do diff antes de aplicar** | **Sim**: prévia de mudanças com "manter/desfazer" |
| [usnistgov/jarvis](https://github.com/usnistgov/jarvis) | 401 | NIST | **Não é assistente**: JARVIS-Tools, ciência de materiais (simulações DFT) | Não. O clone de 323 MB pode ser apagado |
| [affaan-m/JARVIS](https://github.com/affaan-m/JARVIS) | 499 | **sem licença** | Óculos com câmera + reconhecimento facial + agentes que vasculham redes sociais para montar um **dossiê de pessoas** | **Não** (ver abaixo). Só a ideia de pesquisa em fases |
| [code-a2z/jarvis](https://github.com/code-a2z/jarvis) | 141 | MIT | Hub em Streamlit com dezenas de mini-apps (automações, chatbot, jogos, estudo), login Google, perfis de usuário | Ideia: **sistema de plugins** para adicionar comandos |
| [AlexandreSajus/JARVIS](https://github.com/AlexandreSajus/JARVIS) | 528 | **GPL-3.0** | Voz → Deepgram → GPT → ElevenLabs, interface Taipy, mede o tempo de cada etapa | Ideia: **medir as etapas**, que já adotamos. Código não pode ser copiado (GPL) |

## O que já foi incorporado nesta rodada

- **Pesquisa na internet em níveis** (ideia das "fases" do affaan-m, sem a parte invasiva):
  - **simples**: ~3 sites, na própria conversa;
  - **média**: ~15 sites, em segundo plano;
  - **difícil**: ~35 sites, em segundo plano;
  - **extra difícil**: 50 ou mais sites, em segundo plano.

  O relatório vem separado por categorias, com opções (prós e contras), divergências entre as fontes e a lista numerada de fontes. A Jarvis confere quantos sites foram citados de fato, e o relatório vai para `Jarvis/Pesquisas` no Obsidian. A pesquisa roda **isolada**: só busca e leitura de sites, sem as ferramentas do PC.
- **Anexos com PDF, Word, Excel e imagens**, como no danilofalcao. Aqui as imagens são vistas pelo Claude, sem precisar de OCR.
- **Criação de documentos**: Word, PDF, Excel (com fórmulas) e PowerPoint (com notas).

## Próximas melhorias recomendadas (em ordem)

1. **Abrir projetos, programas, sites e pastas por voz.** "Jarvis, abre o projeto MeuApp" → VS Code + terminal na pasta. Vem do ctaylo21, do Jarvis-AI e do code-a2z.
2. **Prévia das mudanças do Claude Code**, inspirada no danilofalcao: depois de uma "execução", mostrar o `git diff` na janela com os botões **Manter** e **Desfazer** (`git restore`).
3. **"Olha minha tela"**: capturar a tela ou a janela ativa e mandar para o Claude, para erros, layouts e mensagens.
4. **Sistema de plugins**, como no code-a2z: cada comando novo vira um arquivo em `jarvis/plugins/`, sem mexer no núcleo.
5. **Tempo de cada etapa na janela** (transcrever, pensar, falar), como no AlexandreSajus, para acompanhar o desempenho.

## O que NÃO será copiado, e por quê

- **affaan-m/JARVIS:**
  - identifica pessoas por foto (reconhecimento facial e busca reversa de rosto) e monta dossiês a partir de redes sociais. Isso viola a privacidade e pode infringir a LGPD;
  - cria contas automaticamente em plataformas, o que viola os termos de uso delas;
  - o repositório não tem licença, então nem o código pode ser reaproveitado.
- **AlexandreSajus/JARVIS:** é GPL-3.0. Copiar o código obrigaria a abrir todo o código da Super Jarvis sob a mesma licença.
- **Reconhecimento de voz não oficial do Google** (usado em tutoriais): mantivemos o Whisper local, porque o áudio não sai do PC.
