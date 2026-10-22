# Cérebro local (reserva offline): medição e opções

Medido em 2026-10-21 neste PC: i5-8265U (4 núcleos / 8 threads), 8 GB de RAM, sem GPU, Windows 11, llama.cpp build 11700
(CPU). Nuvem (Claude/Gemini) continua sendo o cérebro principal; o local é a reserva sem internet.

## Linha de base (modelo atual, Qwen2.5-Coder 1,5B Q4_K_M)
- `llama-bench`: leitura do prompt 54,6 tok/s e geração 8,8 tok/s com 4 threads; com 7 threads (o que o código usava,
  `cpu_count - 1`) a geração caiu para 6,8 tok/s. Ajuste: threads = núcleos físicos (`jarvis/llm/parametros.py`).
- Pelo servidor (25 conversas): geração média 11,3 tok/s, 1º token mediano 0,77 s, RAM de pico 1,75 GB, carga 6,7 s.

## Benchmark de qualidade (25 conversas em português, rubrica automática 0-4 por conversa)
Rubrica: fatos corretos, específico (termos concretos, não vago), português natural (sem inglês/chinês), formato pedido.
Uma tentativa por conversa (não são as 3 tentativas do plano: sem estatística de consistência). Rubrica por regex: é
grosseira e generosa; a diferença real aparece em "fatos" e na leitura das respostas.

| Modelo | fatos (de 25) | nota média | geração | 1º token (mediana) | RAM pico | palavras/resposta |
|---|---|---|---|---|---|---|
| Qwen2.5-Coder 1,5B (atual) | 18 | 3,19 | 11,3 tok/s | 0,77 s | 1,75 GB | 26 |
| Qwen3 1,7B (sem pensar) | 20 | 3,15 | 9,0 tok/s | 1,1 s | 2,24 GB | 44 |
| Qwen3 4B Instruct 2507 | só 10 conversas | só 10 conversas | 3,9 tok/s | 2,9 s | 3,3 GB | 53 (10 conv.) |

Nas 10 conversas em comum (git merge/rebase, resumo, SQLite, lista, CSV com `;`, "confere de novo" 15% de 200,
manga ambíguo, telefone de vizinho, Copa de 2038, cotação do dólar): fatos 4/10 (atual), 10/10 (Qwen3 1,7B), 10/10
(Qwen3 4B). O modelo atual INVENTOU nas 4 conversas de "não sei" (telefone inventado, vencedor da Copa de 2038,
cotação "1.10") e errou o CSV (`sep=','`) e a conta (confirmou 25). Os Qwen3 recusaram, acertaram 30 e `sep=';'`.
Qwen3 1,7B respondeu em INGLÊS em 3 de 25 conversas (ex.: "Okay, let's recheck"); o 4B, em 0. Não foi medido o 4B nas
15 conversas restantes (o pedido do dono foi finalizar). O modelo atual também cola `[[SAVE:...]]` nas respostas e
dá respostas de ~26 palavras: a persona manda "curta e direta" (`contexto.PERSONA`); não alterei (arquivo de outro agente).

Distância até um modelo grande na nuvem: NÃO medida (sem chave/rubrica comparável). Pela leitura, o 4B é bem melhor que
o 1,5B, mas ainda é um modelo pequeno: erra fatos raros e a 3,9 tok/s (~3 palavras/s) uma resposta de 150 palavras leva ~40 s.

## O que ficou instalável (opcional, desligado por padrão: o padrão continua o Coder 1,5B)
- Catálogo (`jarvis/llm/catalogo.py`): `qwen3-4b` (Apache-2.0, 2,38 GB, SHA-256 `3605803b…c67e597`) e `qwen3-1.7b`
  (Apache-2.0, 1,06 GB, SHA-256 `b139949c…a181897`), repositórios `unsloth/*-GGUF` (conversão de terceiros do Qwen oficial;
  o repositório oficial `Qwen/…2507-GGUF` não existe). Todos os modelos agora têm SHA-256 e tamanho reais do Hugging Face.
- Download (`baixar.py`): retomável (Range), reconecta sozinho, confere tamanho e SHA-256; arquivo corrompido é descartado.
  O resume foi exercitado de verdade nos dois downloads do benchmark (conexão caiu e retomou; SHA conferido).
- Parâmetros (`parametros.py`): threads = núcleos físicos, `-np 1`, lote 512, `--cache-reuse 256`, sem mlock, `--no-webui`,
  `-rea off` para o Qwen3 1,7B; aquecimento do prompt do sistema na carga (`servidor._aquecer`).
  NÃO medi o ganho do aquecimento nem de `-np 1`/`--cache-reuse` isoladamente; só a troca de threads foi medida.
- Escolha (`escolha.py`, janela ⚙ Cérebros): lista com aviso de espaço, RAM e velocidade, troca entre instalados e
  "Voltar ao modelo antigo". Instalar não apaga o anterior. Instalar: "instalar cérebro local melhor" (ou o id do modelo).
- Streaming para a janela: NÃO feito (depende do motor de conversa, de outro agente).

## Celular (iPhone 13 Pro Max, 6 GB) — só documentação
`movel/dados/modelos.json` guarda os modelos de PROJETO (fastapi, react…), não modelos de IA; a lista de IA está em
`movel/js/cerebro.js` (não editei). Lista real do WebLLM 0.2.86 (`prebuiltAppConfig`, jsDelivr), em vram_required_MB:
Llama-3.2-1B q4f16 879; gemma3-1b 711; Qwen2.5-1.5B 1630; gemma-2-2b-1k 1583 (contexto 1024); gemma-2-2b 1895;
Qwen3-1.7B 2037; Qwen2.5-3B 2505; Llama-3.2-3B 2264; Phi-3.5-mini-1k 2520; Qwen3-4B 3432; Qwen3.5-2B 2245 (sem
`low_resource`). Todos com contexto 4096 salvo os "-1k". O campo `mb` do `cerebro.js` é essa VRAM, não o download.
Proposta (NÃO testada em aparelho): manter Llama 1B como recomendado; trocar o "Mais capaz" por Qwen3-1.7B
(2037 MB, marcado `low_resource_required`, bom em português, desligar o "pensar" com `enable_thinking:false` — não
verifiquei se a 0.2.86 aceita); não oferecer 3B+ em 6 GB (o Safari limita memória por aba; limite exato desconhecido).
`AJUSTES_DE_JANELA` não foi tocado.
