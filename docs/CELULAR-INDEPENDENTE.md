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
