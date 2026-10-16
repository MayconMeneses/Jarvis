"""Cérebro generativo LOCAL: um modelo de linguagem pequeno rodando no próprio PC, sem API e sem nuvem.

Peças (cada uma num arquivo):
- catalogo.py: modelos recomendados, onde ficam os arquivos e o estado da instalação.
- baixar.py: baixa o motor (llama.cpp) e o modelo (GGUF) só quando o usuário aprova o cartão.
- servidor.py: liga o llama-server em 127.0.0.1 sob demanda e desliga quando fica parado.
- cliente.py: conversa com o servidor (API compatível com OpenAI) ou com Ollama/LM Studio já instalados.
- contexto.py: monta o prompt com o conhecimento curado da Jarvis (RAG) para o modelo pequeno acertar mais.
- cerebro.py: o cérebro "llm" do roteador.
- pensar.py: criar sistemas planejando, escrevendo arquivo por arquivo e conferindo cada um.

Limite honesto: modelos de 1,5 a 3 bilhões de parâmetros em CPU são lentos e bem menos capazes que o Claude.
O conhecimento curado, a verificação do código e a aprovação do usuário compensam parte disso.
"""
