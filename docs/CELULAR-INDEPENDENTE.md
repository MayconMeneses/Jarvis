# Jarvis independente no celular (iPhone 13 Pro Max e outros)

No celular roda **uma Jarvis só dele**, que não fala com o PC: a memória, o conhecimento e o cérebro ficam no próprio aparelho.
É um app web instalável (PWA) em `movel/`, em JavaScript puro, sem servidor e sem conta de desenvolvedor.

## O que ele faz sozinho

- **Motor de regras** (instantâneo, sem internet): hora e data; memória ("lembre que...", "me lembre de pagar a luz amanhã", "o que você
  sabe sobre...", "apague a nota X"); os 59 tópicos de lógica, engenharia, arquitetura e UX, os 8 padrões de projeto e os 15 algoritmos
  do PC (a mesma base, gerada de `jarvis/dev` por `python movel/gerar_dados.py`); contraste, paleta, escala e tokens CSS; geradores
  (tabela SQL, ADR, história de usuário, OpenAPI, CI, Dockerfile).
- **Internet pelo próprio celular:** "pesquise sobre..." e "aprenda sobre..." usam a Wikipédia em português; o resumo vira a nota
  `Aprendizado/<tema>`, marcada como "não verificado".
- **Memória própria:** notas e diário em IndexedDB, só no aparelho. Aba **Memória** para ver, editar, apagar, **salvar cópia** (arquivo JSON
  que você guarda onde quiser) e **restaurar**. O app pede ao iPhone para não apagar esses dados.
- **Avisos ao abrir:** bom dia, lembretes do dia, tópico do dia e treino da semana (às segundas). Um site no iPhone não consegue acordar
  sozinho em segundo plano; por isso os avisos aparecem quando o app é aberto.
- **Voz:** ditado em português e leitura das respostas, em HTTPS (no GitHub Pages já vale).
- **Cérebro de IA no celular (opcional):** aba **Cérebro**. Um modelo pequeno (360M a 1,5B; recomendado o Gemma 3 1B, ~710 MB) é baixado
  uma vez, com a sua confirmação, e roda dentro do iPhone com WebGPU, sem enviar nada para fora. Quando ligado, tudo que o motor de regras
  não entende vai para ele, já com o conhecimento curado, a sua memória e os dados reais (hora, memória) no prompt.

## Limites honestos

- O cérebro de IA exige **Safari com WebGPU (iOS 26 ou mais novo)**. O iPhone 13 Pro Max aceita essa atualização, mas eu não testei
  em um iPhone de verdade: testei a lógica com node e o app no navegador do PC. O desempenho real (velocidade, calor, bateria) você confirma no aparelho.
- Um modelo de até 1B no celular conversa e ajuda com tarefas pequenas, mas erra bem mais que o do PC e muito mais que o Claude.
- Código de terceiros: o cérebro de IA carrega o WebLLM (Apache-2.0, versão fixa 0.2.86) do jsDelivr **só quando você liga o cérebro**; os pesos
  do modelo vêm do Hugging Face. O resto do app não carrega nada de fora (os únicos sites que ele chama são a Wikipédia e o jsDelivr; há teste para isso).
- Aparelhos com mais memória (iPads, iPhones novos) aguentam o modelo de 1,5B; o app mostra a lista e você escolhe.
- App nativo da App Store exigiria um Mac com Xcode e a conta Apple Developer (US$ 99 por ano). Só vale se você precisar de notificações
  push nativas ou de um modelo maior no iPhone.

## Como publicar (você decide quando)

O app é só arquivos estáticos. Para instalar no iPhone ele precisa estar em um endereço HTTPS. A forma mais simples e gratuita é o GitHub Pages:

1. No GitHub: **Settings → Pages → Source: GitHub Actions** (isso torna o site público; o código já é público e **seus dados nunca vão para lá**).
2. **Actions → "Publicar a Jarvis do celular" → Run workflow.** O fluxo roda os testes e publica só `index.html`, `sw.js`, `css/`, `js/`, `dados/` e `icones/`.
3. No iPhone, abra `https://mayconmeneses.github.io/Jarvis/` no Safari e toque em **Compartilhar → Adicionar à Tela de Início**.

Enquanto o Pages não for ligado, nada é publicado. Para testar no PC antes: `cd movel && python -m http.server 8790` e abra `http://127.0.0.1:8790`.

## Para quem mexe no código

- `movel/js/` tem módulos pequenos (memória, saber, motor, design, gerar, aprender, cérebro, contexto, proativo, interface).
- Testes: `node --test movel/testes/*.test.mjs` (o cérebro é testado com um WebLLM falso) e
  `python -m pytest tests/test_movel.py` (confere que os cálculos do celular dão o mesmo resultado que os do PC e que a base está em dia).

## Suas chaves de API no celular (Gemini, NVIDIA, Brave e outras)

Na aba **Cérebro → Nuvem** você cadastra as chaves que já tem. A chave fica **só neste aparelho** (IndexedDB), **fora da cópia de segurança**, e só vai
para o provedor que você escolheu. Cadastrar testa a chave antes de guardar; se o modelo padrão foi aposentado, o app acha outro que a chave enxerga.

| Serviço | Funciona direto no celular? | Como |
|---|---|---|
| **Google Gemini** | Sim | Provedor "Google Gemini" + a chave. |
| OpenAI, Groq, OpenRouter | Sim | Idem (ou "Outro", com a URL base). |
| **NVIDIA** | **Não**: o site da NVIDIA bloqueia chamadas do navegador (sem CORS; verificado) | Precisa de um proxy seu (abaixo). |
| **Brave Search** | **Não**, pelo mesmo motivo (verificado) | Mesmo proxy. Quando cadastrado, "pesquise/aprenda sobre..." passa a usar o Brave (várias fontes) e cai para a Wikipédia se ele falhar. |

Ordem de uso (você escolhe na mesma tela): **aparelho primeiro** (padrão, mais privado) ou **nuvem primeiro** (mais capaz; a pergunta vai ao provedor). Se um falha, tenta o outro.

### Proxy grátis para NVIDIA e Brave (Cloudflare Workers), uma vez só
1. Crie uma conta grátis em dash.cloudflare.com → **Workers & Pages → Create → Worker**.
2. Cole o conteúdo de `movel/proxy/nvidia-worker.js` no editor e toque em **Deploy**. Anote o endereço, por exemplo `https://jarvis-proxy.seunome.workers.dev`.
3. No app do celular, em **Nuvem**: **NVIDIA (por proxy)** com a URL base `https://jarvis-proxy.seunome.workers.dev/v1` e a sua chave da NVIDIA; **Brave Search (por proxy)** com a URL `https://jarvis-proxy.seunome.workers.dev` (sem `/v1`) e a sua chave do Brave.

O proxy **não guarda chave nenhuma**: só repassa o cabeçalho de autenticação, aceita apenas pedidos vindos de `https://mayconmeneses.github.io` (a constante `ORIGEM` no
arquivo; mude se publicar o app em outro endereço) e só as rotas `/v1/...` (NVIDIA) e `/brave/res/v1/...` (Brave). Quem souber o endereço do seu proxy não consegue usá-lo sem a origem e a chave.

## Oficina: a IDE do celular

A aba **Oficina** faz no celular o que a Oficina do PC faz:

- **Projetos e arquivos** (editor de texto, salvar, apagar, **desfazer** com as últimas 20 versões de cada arquivo). Ficam só no aparelho, como notas
  `Oficina/<projeto>/<arquivo>`: entram na cópia de segurança e aparecem na aba Memória. Limites: 60 arquivos por projeto, 20 000 caracteres por arquivo.
- **Modelos prontos** (os mesmos do PC: FastAPI, Express, React e HTML, sozinhos ou combinados; `dados/modelos.json`, gerado por `python movel/gerar_dados.py`).
- **Rodar e Testar** num **ambiente isolado**: um iframe `sandbox="allow-scripts"` (sem acesso à memória, às chaves nem ao IndexedDB do app) com política de
  segurança própria, e dentro dele um Worker (um laço infinito é interrompido pelo tempo limite: 10 s em JavaScript, 60 s em Python). JavaScript roda sem rede;
  testes usam `require('node:test')` e `require('node:assert')`. Python roda com o Pyodide baixado do jsDelivr na primeira vez (~10 MB, o app pergunta antes).
- **Baixar ZIP** do projeto (salve em Arquivos).
- **Criar com IA**: a IA (cérebro do aparelho ou chave de nuvem, na ordem que você escolheu) planeja os arquivos, escreve um por vez, confere a sintaxe (JS/JSON),
  roda os testes JavaScript no ambiente isolado e pede até 2 correções. O que ela escreve é só texto; o programa em si só roda quando você toca em Rodar.
  Testes em Python gerados pela IA ficam sem rodar automaticamente (para não baixar o Pyodide sem você pedir); rode com **Testar**.

Limite honesto: o isolamento protege de acidentes e de código mal escrito, não substitui ler o código antes de rodar. Foi validado no Chromium (JavaScript, Python
com Pyodide, laço infinito interrompido, ZIP); **não foi testado no Safari do iPhone**.

## Aprender sozinha e avaliar o cérebro (paridade com `jarvis/autonomo` e `jarvis/llm/avaliar.py`)

Na aba **Cérebro**, seção "Aprender sozinha e avaliar o cérebro":

- **Aprender sozinha** (desligado por padrão; a escolha fica no aparelho). Ligada, e com o app **aberto e sem uso por 10 minutos**, a Jarvis lê o diário
  (linhas "Pedido:" dos últimos 14 dias), acha as perguntas do tipo "o que é X / explique X / como usar X" que a base **não** conhece, escolhe a mais
  repetida, pesquisa (Brave por proxy se cadastrado, senão Wikipédia, o mesmo código do "aprenda sobre") e guarda o resumo como nota `Aprendizado/<assunto>`.
  No máximo **3 assuntos por dia**; um assunto que falhou não é tentado de novo. Diga **"o que você aprendeu"** para listar. Tudo vem da internet e não é verificado.
- **Avaliar o cérebro** (botão **Avaliar agora**, ou "avaliar cérebro"; "como está meu cérebro" mostra a última nota): 5 tarefas pequenas de JavaScript
  (`ehPar`, `somaLista`, `maior`, `palindromo`, `fatorial`) são pedidas ao cérebro do aparelho (ou à nuvem, na ordem escolhida), os testes escondidos rodam no
  ambiente isolado da Oficina e a **nota de 0 a 100** é guardada com data e modelo (compara com a anterior). Sem cérebro ligado, ela explica o que falta.
  Com "Aprender sozinha" ligada, a avaliação também se repete a cada 7 dias, no mesmo momento ocioso.
- Código: `movel/js/autonomo.js`, `agendador.js`, `avaliar.js`, `motor-autonomo.js`, `painel-autonomo.js`; testes em `movel/testes/autonomo.test.mjs`.

Limite honesto: o iPhone não deixa um site rodar em segundo plano. **Com o app fechado ou a tela bloqueada nada é estudado**; ao contrário do PC, não existe agendador
independente. Os assuntos têm o acento removido no nome da nota (ex.: `Aprendizado/computacao quantica`). Não foi testado no Safari do iPhone.

## Orbe reativo, memória viva e grafo do Second Brain

**Orbe (Canvas 2D, sem biblioteca)** no cabeçalho, no lugar do ponto: estados **ocioso / ouvindo / pensando / falando** (e o mesmo estado em texto ao lado, em "pronta / ouvindo… / pensando… / falando…").
30 fps em atividade, 15 parado, 10 no modo suave; resolução limitada a 2x; pausa quando a aba fica oculta. Chave **Animação do orbe** (Automática, Completa, Suave, Desligada), lembrada no
aparelho: Automática segue o "reduzir movimento" do sistema (vira Suave). Código: `orbe.js`, `orbe-desenho.js`, `orbe-voz.js`, `orbe-ui.js`, ligados em `chat.js`.

- **Fala:** o navegador não entrega o áudio da voz (SpeechSynthesis), então a animação é **pelo ritmo do texto, não pelo som real** (a tela diz isso). Ela usa um envelope sintético por sílabas
  e pontuação (ajustado pelo `rate`), abre e fecha em `onstart/onend` e dá um pulso a cada palavra em `onboundary`, que também reajusta o relógio (se o Safari não mandar `onboundary`, fica só o envelope).
- **Escuta:** animação sintética guiada por `start / speechstart / result / end` do reconhecimento de fala. O app **não** abre `getUserMedia` junto com o reconhecimento. O `AnalyserNode` do microfone
  real existe (`analisadorMicrofone`, `ligarEscuta(..., { micReal: true })`) mas fica **desligado e sem botão**: no iPhone os dois juntos podem derrubar um ou trocar a saída de áudio, e isso ainda não foi testado.

**Memória viva com aprovação** (`memoria-viva.js`, `cartao-memoria.js`): o modelo (do aparelho ou da nuvem) pode terminar a resposta com `[[SAVE:area|titulo|texto]]`. Áreas aceitas:
metas, trabalho, projetos, financas, aprendizado, saude, relacoes, meta. Título até 60 caracteres, sem `/`, `\` nem `..`; texto até 500, uma linha; no máximo 2 por resposta; qualquer formato fora disso é
descartado. A linha **some** do texto exibido, falado e guardado na conversa e vira o cartão **"Guardar esta lembrança?"** com **Guardar / Descartar**. **Nada é gravado sozinho.** Se já existe nota com o mesmo
título, o cartão mostra Antes/Depois e só substitui se você tocar em Guardar. Se o turno usou dados de site, notícia ou pesquisa, o cartão avisa. A nota fica em `<Área>/<título>` (ex.: `Saúde/Dormir cedo`),
tipo "viva", com a origem escrita no fim. A instrução ao modelo é uma frase curta em `contexto.js`, dentro do `LIMITE_TOTAL`.

**Grafo** (aba Memória, botão **Grafo**; `areas.js`, `grafo-desenho.js`, `painel-grafo.js`): núcleo pulsante, 8 áreas com cor fixa (metas #fbbf24, trabalho #ff5547, projetos #8b7cff, finanças #f7931a,
aprendizado #2dd4ff, saúde #10b981, relações #ec4899, meta #8a90a6) e um ponto por nota (até 150, repartidas entre as áreas). A área vem do prefixo do nome (Projetos/ e Oficina/ = projetos; Aprendizado/;
Perfil/ e Trabalho/ = trabalho; Metas/ e Lembretes/ = metas; Lembranças/ e Diário/ = meta; Finanças/, Saúde/, Relações/; o resto = meta). Tamanho do ponto = ligações (`[[nota]]` e a área); arestas curvas;
alguns pulsos de luz. Toque num ponto abre a nota no editor da aba. 12 fps parado, pausa com aba oculta ou painel fechado e fica parado se a animação estiver Suave/Desligada. Os nomes das notas só são
desenhados com `fillText` (nunca HTML); há teste de XSS.

Testes: `movel/testes/visual.test.mjs`, `vivo.test.mjs`, `grafo.test.mjs`. Cache do app: `jarvis-movel-7`. Validado no Chromium a 390 px (cartão ponta a ponta com a nuvem simulada, grafo, toque no nó, fala simulada).
**Não testado:** Safari/iPhone, conflito entre microfone e reconhecimento, `onboundary` no iOS, voz real do aparelho.
