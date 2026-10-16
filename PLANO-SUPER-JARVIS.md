# Plano da Super Jarvis

Data: 14/10/2026 · Status: proposta para aprovação, nenhum código escrito ainda.

## 1. Objetivo

Uma assistente para Windows, com instalador, que:

1. conversa por voz e por texto em português;
2. executa tarefas no computador a pedido;
3. filtra e organiza os e-mails do Gmail e do Hotmail/Outlook;
4. ajuda a melhorar o desempenho do PC;
5. usa o Claude como cérebro principal **sem custo extra além das assinaturas que você já tem**.

## 2. Restrições encontradas (CONFIRMADAS no seu PC)

| Item | Valor | Impacto |
|---|---|---|
| CPU | Intel i5-8265U, 4 núcleos | Rodar modelos de IA localmente fica lento |
| RAM | 7,9 GB | Não comporta um LLM local junto com o Windows e o navegador |
| GPU | Intel UHD 620 (integrada) | Sem CUDA, então nada de IA local acelerada |
| Disco C: livre | 23 GB | Evitar ferramentas pesadas (ex.: Rust + Visual Studio Build Tools, cerca de 6 a 8 GB) |
| Já instalados | Python 3.14, Node, Git, Claude Code | Boa base, só falta pouca coisa |

**Conclusão:** a Jarvis precisa ser **leve no PC e usar IA na nuvem**. No computador ficam só as partes pequenas: a palavra de ativação, a transcrição curta e a interface. Por isso o Ollama/LLM local que alguns projetos usam está fora deste plano.

## 3. O que aprendemos com os repositórios analisados

Os repositórios estão em `_referencias/` e servem **só para estudo**. Nenhum código é copiado.

| Projeto | Licença | O que vamos aproveitar (como ideia) |
|---|---|---|
| [ethanplusai/jarvis](https://github.com/ethanplusai/jarvis) | Uso pessoal apenas, proíbe uso comercial | **A ideia central de custo:** o cérebro é um processo `claude -p --input-format stream-json --output-format stream-json` rodando na **sua assinatura**. Ele remove `ANTHROPIC_API_KEY` do ambiente para nunca cobrar por API sem querer. Memória em arquivos Markdown, um fato por arquivo. |
| [open-jarvis/OpenJarvis](https://github.com/open-jarvis/OpenJarvis) | Apache-2.0 (pode reaproveitar com crédito) | Camada de "motores" de IA trocáveis (inclui NVIDIA NIM, Gemini e Ollama via API compatível com OpenAI), conectores de Gmail/Outlook, **scanner de prompt injection**, agente de resumo matinal. |
| [isair/jarvis](https://github.com/isair/jarvis) | Não comercial | Fluxo de voz completo (faster-whisper, Piper, VAD), assistente de configuração inicial, ferramentas via MCP, empacotamento com PyInstaller. |
| [Priler/jarvis](https://github.com/Priler/jarvis) | CC BY-NC-SA (não comercial) | Assistente offline com Rust + Tauri. Mostra que o Tauri exige o kit do Rust, pesado demais para o seu disco. *(Clone removido para liberar 1,5 GB.)* |
| [akshayaggarwal99/jarvis-ai-assistant](https://github.com/akshayaggarwal99/jarvis-ai-assistant) | MIT | Ditado "segure a tecla e fale", limpeza de palavras de preenchimento, prompts editáveis. |
| [sukeesh/Jarvis](https://github.com/sukeesh/Jarvis) | MIT | Arquitetura de **plugins**: cada habilidade é um arquivo. |

Como três dos projetos proíbem uso comercial, escrever do zero também protege você se um dia quiser vender ou distribuir a Jarvis.

### Peças prontas encontradas no GitHub (componentes, não Jarvis inteiras)

| Função | Projeto | ⭐ | Licença |
|---|---|---|---|
| Palavra de ativação "Hey Jarvis" (já vem treinada, leve em CPU) | [dscripka/openWakeWord](https://github.com/dscripka/openWakeWord) | 2,8k | Apache-2.0 |
| Fala para texto | [SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 25,8k | MIT |
| Fala para texto em tempo real com detecção de voz | [KoljaB/RealtimeSTT](https://github.com/KoljaB/RealtimeSTT) | 10,1k | MIT |
| Voz natural em pt-BR (online, grátis) | [rany2/edge-tts](https://github.com/rany2/edge-tts) | 12,2k | verificar (LGPL) |
| Voz offline de reserva | [rhasspy/piper](https://github.com/rhasspy/piper) | 11,3k | MIT (versão arquivada) |
| Controle do Windows por IA (MCP) | [CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | 8,9k | MIT |
| Automação de janelas | [pywinauto/pywinauto](https://github.com/pywinauto/pywinauto) | 6,2k | BSD-3 |
| Gmail via MCP | [taylorwilsdon/google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | 3,3k | MIT |
| Referência de triagem de e-mail com IA | [elie222/inbox-zero](https://github.com/elie222/inbox-zero) | 12,4k | verificar |
| Pipeline de voz (se precisarmos de algo mais robusto) | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) | 16,4k | BSD-2 |
| Lista de otimizações do Windows (só como referência) | [itsfatduck/optimizerDuck](https://github.com/itsfatduck/optimizerDuck) | 10,4k | verificar |

## 4. IA sem pagar a mais: o "roteador de cérebros"

| Cérebro | Como conecta | Custo | Para quê | Cuidado |
|---|---|---|---|---|
| **Claude** (principal) | `claude -p` (Claude Code já instalado), logado na sua assinatura | Já incluso na assinatura (consome os limites de 5 h e 7 dias) | Tarefas complexas, decisões, usar ferramentas do PC | A central de ajuda da Anthropic permite usar `claude -p` com o seu plano **para uso pessoal**. Para **distribuir** a Jarvis a outras pessoas, os termos pedem que cada um use a própria chave de API. A política mudou várias vezes em 2026 e precisa ser reconferida antes de distribuir. |
| **Gemini** | Chave gratuita do Google AI Studio (modelos Flash) | Grátis, com limite diário | Respostas rápidas, resumos, classificação de e-mails | A assinatura Gemini AI Pro **não** aumenta os limites da API, só os do Gemini CLI. O Google avisa que usar o login do CLI em ferramentas de terceiros pode suspender a conta, então não faremos isso. |
| **NVIDIA NIM** | Chave grátis em build.nvidia.com (API compatível com OpenAI) | Grátis, cerca de 40 pedidos/min | Reserva quando o Claude ou o Gemini estiverem no limite, e triagem em lote | É liberado "para prototipagem", não para produção. |

Regra do roteador: tarefa simples vai para Gemini Flash ou NIM; tarefa que precisa agir no PC ou raciocinar vai para o Claude; quando um atinge o limite, cai para o próximo.

## 5. Arquitetura proposta

```
┌──────────── Interface (janela de chat + ícone na bandeja) ────────────┐
│  pywebview (usa o Edge WebView2 do Windows) + pystray                 │
└───────────────▲───────────────────────────────────▲───────────────────┘
                │ texto                             │ áudio
┌───────────────┴──────────┐        ┌───────────────┴──────────────────┐
│  Núcleo Jarvis (Python)  │◄──────►│ Voz: openWakeWord → faster-whisper│
│  • roteador de cérebros  │        │      (pt-BR) → edge-tts / Piper   │
│  • memória (Markdown +   │        └──────────────────────────────────┘
│    SQLite)               │
│  • aprovação de ações    │──► claude -p (assinatura) / Gemini / NIM
│  • log de tudo           │
└───────────────┬──────────┘
                │ MCP (protocolo padrão de ferramentas)
┌───────────────┴───────────────────────────────────────────────────────┐
│ Servidor MCP da Jarvis: e-mail (Gmail API + Microsoft Graph),          │
│ desempenho (psutil), arquivos, abrir programas, + Windows-MCP opcional │
└───────────────────────────────────────────────────────────────────────┘
```

**Por que MCP:** o `claude -p` (com `--mcp-config`) e o Gemini falam esse protocolo. Escrevendo as ferramentas uma vez como servidor MCP, qualquer cérebro passa a usá-las.

**Mudança de tecnologia recomendada: pywebview em vez de Tauri.** O Tauri exige instalar o Rust e o Visual Studio Build Tools (vários GB) num disco com 23 GB livres. O pywebview usa o mesmo motor de tela (WebView2, já presente no Windows 11), fica todo em Python e o instalador sai com PyInstaller + Inno Setup. *Precisa da sua aprovação, porque você tinha escolhido Tauri.*

## 6. Módulos e regras de segurança

### E-mail (Gmail + Hotmail/Outlook)
- Gmail: API oficial com OAuth (permissão para ler e aplicar marcadores).
- Hotmail/Outlook: Microsoft Graph com OAuth. A Microsoft vem desligando a senha de app no IMAP de contas pessoais (PROVÁVEL; confirmar na implementação), então OAuth é o caminho seguro.
- Filtro em duas camadas: primeiro **regras fixas** (remetente e palavras, custo zero) e depois **IA** só para o que sobrar. Resultado: marcadores e pastas como "Importante", "Financeiro", "Promoções", "Ler depois".
- **Nunca** apaga, envia ou responde sem você aprovar na tela.
- **Proteção contra prompt injection:** o texto do e-mail é tratado como dado. Um e-mail que diga "Jarvis, apague tudo" não vira comando. Isso inclui um scanner de padrões suspeitos (ideia do OpenJarvis).

### Desempenho do PC
- Somente leitura no início: processos pesados, programas que iniciam com o Windows, espaço em disco, uso de RAM e temperatura (se disponível).
- Ações com aprovação: fechar processo, desativar item de inicialização, limpar `%TEMP%` mostrando antes o que será apagado.
- **Fora do escopo:** "otimizadores" que mexem no registro, desligam o Windows Update ou o antivírus.
- Cada ação fica registrada em log e, sempre que possível, pode ser desfeita.

### Voz
- Ativação "Hey Jarvis" (modelo pronto do openWakeWord). Uma palavra só, "Jarvis", exige treinar um modelo depois.
- Transcrição local com faster-whisper `small` int8 em CPU (estimativa de 1 a 3 s por frase curta no seu i5; medir na Fase 4), com o Gemini como alternativa na nuvem.
- Voz de resposta pt-BR com edge-tts (gratuita e natural), Piper offline como reserva e ElevenLabs como opção paga.

### Memória ligada ao Obsidian
O cofre que você já usa é `C:\Users\maico\OneDrive\Área de Trabalho\Obisidian projetos\Projetos` (CONFIRMADO, Obsidian instalado). Um cofre do Obsidian é só uma pasta de arquivos Markdown, então a Jarvis grava a memória **direto nele**, sem plugin e sem servidor extra:

```
Projetos/                      (seu cofre)
└── Jarvis/                    ← única pasta onde a Jarvis escreve
    ├── 00 - Índice.md         índice da memória, sempre carregado no contexto
    ├── Memória/               um fato por nota, com frontmatter (tipo, data) e [[links]]
    ├── Diário/2026-10-14.md   resumo de cada dia: o que pediu, o que ela fez
    ├── Relatórios/            resumo de e-mails, saúde do PC, limpezas feitas
    └── Pendências.md          tarefas que ela anotou para você
```

- **Você enxerga e corrige tudo** no Obsidian: editou uma nota, a Jarvis passa a usar a versão nova. Os `[[links]]` aparecem no grafo.
- **Leitura do resto do cofre** (ex.: `MM System Creator/`) para contexto quando você pedir ("Jarvis, o que falta no MM System?"). Ela **não escreve** fora da pasta `Jarvis/` sem aprovação.
- Busca nas notas por palavra-chave primeiro (rápido e leve); busca por significado só se o volume crescer.
- Abrir uma nota direto no app via link `obsidian://open?vault=Projetos&file=...`.
- SQLite fica só para dados técnicos (log de ações e uso dos cérebros), não para a memória.
- Dados pessoais são removidos antes de ir para a nuvem quando possível.

### Memória própria, sem depender do Obsidian (decisão de 2026-10-15)
**Status (2026-10-15): passos 2, 3 e 4 feitos.** `jarvis/memory_db.py` (SQLite + FTS5) é a memória de toda a Jarvis; o Obsidian só entra por importação automática única, `--importar-obsidian` e `--exportar-memoria`; a janela "◈ Memória" lista, busca, edita, apaga e exporta. A classe `Vault` e a seção "Memória ligada ao Obsidian" acima ficam como histórico. **Passo 5 (empacotamento) feito em 2026-10-16:** o instalador leva o modelo Whisper em `{app}\modelos` (gerado por `packaging\baixar_modelo.py`; sem ele, download único para `%LOCALAPPDATA%\SuperJarvis\modelos`), o wake word e o VAD já iam no pacote, e a Jarvis detecta Claude Code e git ao abrir (`jarvis/environment.py`), avisando na janela. Decisão sobre o modelo: embutir o `small`, pois o dono pediu "tudo dentro do instalador" e o `base` errou ~60% das palavras contra ~11% do `small`; o custo é ~0,5 GB a mais no instalador, e quem preferir um instalador pequeno gera com `--nenhum`. Trade-off assumido: a Jarvis não lê mais o resto do cofre do Obsidian, só o que foi importado de `Jarvis/`.

Objetivo do dono: a Jarvis vira um aplicativo com instalador e **tudo que ela precisa vem dentro do instalador**. A memória não pode exigir Obsidian (nem qualquer outro programa).

**Levantamento do que hoje depende de algo de fora** (CONFIRMADO no código):

| Dependência | Onde | Situação para o instalador |
|---|---|---|
| Cofre do Obsidian (`obsidian_vault`) | `memory.py` (classe `Vault`), `briefing.py`, `ui/app.py` (diário), `mcp_server.py` (lembrar, buscar_notas, ler_nota, perfil de vagas), `dev/projects.py` e `dev/runs.py` (ficha e relatórios dos projetos), `__main__.py` (índice no prompt) | **Trocar**: é o assunto desta seção |
| Painel do Dashboard Universal | `jarvis/dashboard/painel.html` | Já embutido |
| Modelos de voz "Hey Jarvis" (openWakeWord) | dentro do pacote Python | Já vão no pacote; conferir no PyInstaller |
| Modelos Whisper (base 142 MB, small 464 MB) | baixados na 1ª vez para `~/.cache/huggingface` | **Decidir**: embutir o `base` no instalador ou baixar na instalação com barra de progresso |
| Modelo de significado (MiniLM, 122 MB) | `~/.cache/huggingface` | Só entra se a busca por significado for usada; hoje não é obrigatória |
| Claude Code (`claude`) | executável externo, usa a assinatura do dono | **Não dá para embutir** (licença e login). O instalador/primeira abertura detecta e guia a instalação e o login; sem ele a Jarvis cai no Gemini/NIM ou no modo independente |
| `git` | projetos de código, estado e revisão | Detectar; se faltar, as funções de projeto avisam em vez de quebrar |
| Python e bibliotecas | venv do dono | O instalador leva o runtime (PyInstaller) |
| Internet | voz de resposta (edge-tts), clima, notícias, vagas, IA em nuvem | Inevitável; já degrada com aviso |
| Credenciais de e-mail | `config_dir()/gmail_client_secret.json` e tokens no cofre do Windows (DPAPI) | Por usuário, ficam fora do instalador de propósito |

**Desenho da memória única**
- **Um arquivo SQLite** em `%APPDATA%\SuperJarvis\memoria.db` (sobrevive a desinstalar e atualizar; backup = copiar um arquivo). Python já traz o `sqlite3`: nada a instalar.
- Tabelas: `memorias` (título, fato, resumo, criado, atualizado), `diario` (data, hora, texto), `relatorios` (nome, conteúdo, data), `projetos_fichas` (projeto, seção, texto, data), `perfil` (chave, valor, para o perfil de vagas) e um índice de busca **FTS5** (rápido e leve; mantém a regra do PC fraco).
- **Mesma interface da `Vault`** (`remember`, `memories`, `index_text`, `search`, `read`, `diary`, `save_report`, mais ficha de projeto e perfil), então `briefing`, `app`, `mcp_server`, `projects` e `runs` trocam só de onde vêm os dados. As ferramentas MCP mantêm os nomes.
- **Obsidian passa a ser opcional**: (1) importação única das notas que já estão em `Jarvis/` no cofre, sem apagar nada; (2) exportação para Markdown, se o dono quiser continuar vendo tudo no Obsidian (o banco é a fonte da verdade, o Markdown é cópia). Sem cofre configurado, tudo funciona igual.
- A tela da Jarvis ganha um visualizador simples da memória (listar, buscar, editar, apagar), porque sem Obsidian o dono precisa de um jeito de ver e corrigir o que ela guardou.
- Regras mantidas: nada de senhas, documentos ou dados bancários na memória; conteúdo de e-mail e notícia nunca vira memória sem passar pelo dono; dados pessoais saem antes de ir para a nuvem quando possível.

**Ordem sugerida**
1. Reconciliar o branch com a `main` (a `main` recebeu a Fase 8 e a interface HUD; o branch tem ficha de projeto, projeto novo, dashboard e fila estável).
2. Criar `jarvis/memory_db.py` com a interface acima e testes; migrar as chamadas para uma fábrica única `open_memory(cfg)`.
3. Importador do `Jarvis/` do Obsidian e exportador opcional para Markdown.
4. Visualizador de memória na janela.
5. Fechar o levantamento de empacotamento (modelo Whisper, wake word, detecção do Claude Code e do git) no instalador.

### Jarvis independente, sem nenhuma IA (decisão de 2026-10-16)
O dono quer que a Jarvis funcione **sem API e sem nenhuma IA**, só com a inteligência dela e a internet, sem depender de terceiros. Feito: o interruptor `somente_independente` (⚙ Cérebros) deixa só o motor próprio (`jarvis/local/`) no roteador, e o motor ganhou habilidades próprias em `jarvis/local/skills.py` (memória, perfil, projetos, dashboards, sessões do Claude Code), além do que já tinha (abrir, PC, clima, notícias, vagas, pesquisa com resumo extrativo).
Avaliado e **não adotado**: o OpenJarvis (open-jarvis/OpenJarvis, Apache 2.0). A configuração dele gira em torno de modelos locais (Ollama/vLLM; os exemplos vão de `qwen3.5:4b` a um servidor com 8 A100) e o resumo diário usa voz paga da OpenAI, o que contradiz "sem IA" e os limites do PC de 8 GB. A licença permitiria reaproveitar partes que não são modelo (catálogo de skills, `doctor`, personas) com atribuição; fica como ideia futura. Próximo passo natural: mais habilidades por regras (e-mail por filtros do dono, agenda, lembretes) e melhor extração de texto na pesquisa.

### Rotina ao abrir (briefing)
Sempre que a Jarvis abre (ou no primeiro uso do dia), ela fala com você:

1. **Saudação:** cumprimenta pelo nome e pergunta como você está. A resposta pode ir para o `Diário/` do dia, se você quiser.
2. **Clima onde você está:** API [Open-Meteo](https://open-meteo.com), gratuita e sem chave. A localização é a cidade que você configurar (mais privado). Detecção automática pelo IP fica como opção, com precisão aproximada.
3. **Notícias relevantes:** feeds RSS gratuitos de portais brasileiros e internacionais. A IA escolhe as 3 a 5 mais importantes e resume em poucas linhas.
4. **Notícias de tecnologia:** feeds de tecnologia (portais brasileiros e a API do Hacker News), priorizando os temas que você usa: desenvolvimento web, IA e as stacks dos seus projetos.
5. **Vagas de desenvolvimento** compatíveis com o seu perfil (ver abaixo).
6. **Pendências:** e-mails importantes e tarefas abertas no Obsidian.

Tudo é mostrado na tela e lido em voz alta numa versão curta. O briefing completo fica salvo em `Jarvis/Relatórios/` no Obsidian.

### Vagas de emprego
- **Fontes legais e gratuitas:** repositórios de vagas no GitHub, onde cada vaga é uma *issue* (ex.: comunidades `frontendbr/vagas` e `backend-br/vagas`), e APIs públicas de vagas remotas (ex.: Remotive, Arbeitnow). Sites que proíbem robôs nos termos de uso, como o LinkedIn, **não** serão raspados.
- **Compatibilidade:** você mantém um `Jarvis/Perfil Profissional.md` no Obsidian com stack, nível, cidade, remoto ou presencial e pretensão. A IA dá uma nota para cada vaga e explica o porquê.
- A Jarvis **nunca se candidata sozinha**. Ela mostra a vaga, o link e, se você pedir, um rascunho de mensagem ou de ajuste do currículo. Quem envia é você.
- Vagas já vistas ficam marcadas para não repetir.

### Aprendizado contínuo
"Aprender" aqui significa **memória e preferências que crescem**, não treinar um modelo. Isso é o que funciona no seu PC e sem custo:
- Ao fim de cada conversa, ela extrai fatos novos ("prefere vagas remotas", "está estudando X") e grava em `Jarvis/Memória/` com `[[links]]`.
- Você pode avaliar briefings e sugestões ("isso foi útil?"). As avaliações ajustam o que entra nas notícias e nas vagas.
- Uma vez por semana, ela consolida a memória: junta notas repetidas, corrige o que ficou velho e gera um resumo "o que aprendi sobre você esta semana" para você revisar no Obsidian.
- Você tem a palavra final: apagou ou editou a nota, ela esqueceu ou corrigiu.

### Parceira de desenvolvimento de sistemas
- Para programar, a Jarvis **chama o Claude Code** (`claude -p`) dentro da pasta do projeto, com a sua assinatura, no mesmo modelo do ethanplusai/jarvis: conversa sobre a ideia, grava a especificação, você aprova e o Claude Code executa.
- Ela lê as notas do projeto no Obsidian (ex.: `MM System Creator/_Current State.md`, `_Next Steps.md`) para saber onde você parou.
- Comandos como "Jarvis, o que falta no MM System?" ou "Jarvis, cria um plano para a tela de login" viram respostas baseadas nas suas notas e no código.
- Ela avisa quando uma sessão do Claude Code está esperando a sua resposta.

## 7. Fases de construção

Cada fase termina com algo funcionando e testado.

| Fase | Entrega | Como validar |
|---|---|---|
| **0. Fundação** | Estrutura do projeto, ambiente Python, configuração, logs, ponte com o `claude -p` em texto | Perguntar algo pelo terminal e receber a resposta do Claude sem chave de API |
| **1. Interface** | Janela de chat + ícone na bandeja + roteador Claude/Gemini/NIM | Conversar pela janela; desligar um cérebro e ver o próximo assumir |
| **2. Desempenho do PC** | Servidor MCP com as ferramentas de leitura e depois as ações com aprovação | "Jarvis, por que meu PC está lento?" traz dados reais |
| **3. E-mail** | Gmail + Outlook: ler, classificar, aplicar marcadores; resumo da caixa | Classificar os últimos 50 e-mails e conferir o resultado |
| **4. Voz** | Ativação + transcrição + fala | Medir o atraso real no seu notebook |
| **5. Memória e rotina** | Memória no Obsidian; saudação ao abrir; clima, notícias gerais e de tecnologia | Reiniciar e verificar se ela lembra; briefing aparece e é salvo no Obsidian |
| **6. Vagas** | Busca em fontes legais, nota de compatibilidade com o seu perfil, sem repetir | Conferir 10 vagas sugeridas e se fazem sentido para você |
| **7. Parceira de desenvolvimento** | Ponte com o Claude Code nos seus projetos + leitura das notas do projeto | Pedir o status do MM System e um plano de tarefa |
| **8. Instalador** | `.exe` com Inno Setup, iniciar com o Windows, desinstalador | Instalar num usuário limpo do Windows |

## 8. Decisões pendentes

1. Trocar Tauri por **pywebview** (recomendado por causa do disco e da falta do Rust)?
2. A Jarvis será **só para você** ou pretende distribuir/vender? Isso muda a regra de uso da assinatura do Claude.
3. Qual nome de ativação: "Hey Jarvis" (pronto) ou "Jarvis" (exige treino)?

## 9. Observações

- A pasta `_referencias/` (240 MB) pode ser apagada depois do estudo. O OneDrive está desativado, então ela não sincroniza; fica fora do git pelo `.gitignore`.
- Os números de limite (NVIDIA cerca de 40/min, cotas do Gemini) vêm de fontes secundárias e mudam com frequência. Conferir nos painéis oficiais ao criar as chaves.

## Fontes
- [Use the Claude Agent SDK with your Claude plan (Anthropic)](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan)
- [Anthropic reinstates third-party agent usage on Claude subscriptions (VentureBeat)](https://venturebeat.com/technology/anthropic-reinstates-openclaw-and-third-party-agent-usage-on-claude-subscriptions-with-a-catch)
- [Claude Code terms of service explained (Autonomee)](https://autonomee.ai/blog/claude-code-terms-of-service-explained/)
- [Is NIM free? (fórum NVIDIA)](https://forums.developer.nvidia.com/t/is-nim-free/369368)
- [NVIDIA NIM rate limit 40 RPM (fórum NVIDIA)](https://forums.developer.nvidia.com/t/request-for-nvidia-nim-api-rate-limit-increase-40-200-rpm-agentic-development-workflow/378941)
- [Gemini CLI e Code Assist com limites maiores (Google)](https://blog.google/technology/developers/gemini-cli-code-assist-higher-limits/)
- [Gemini API pricing changes 2026 (AgentDeals)](https://agentdeals.dev/gemini-api-pricing-changes)
