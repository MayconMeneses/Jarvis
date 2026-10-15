# Comparação: Jarvis-AI (Breno, MIT) × Super Jarvis

Data: 15/10/2026. O código do Jarvis-AI foi analisado em `_referencias/Jarvis-AI-main` (cerca de 21 mil linhas, licença MIT).

## O que a Super Jarvis já faz (igual ou melhor)

| Jarvis-AI | Super Jarvis |
|---|---|
| Gemini 1.5 Flash (chave paga/gratuita) | Claude pela assinatura (sessão aberta, ~1,5 s), com Gemini e NVIDIA de reserva |
| pyttsx3 (voz robótica) | Voz neural Francisca, falando frase a frase; Maria offline |
| Reconhecimento pelo Google (envia o áudio) | Whisper local + "Hey Jarvis" local + bipe |
| Memória em JSON/SQLite | Memória no Obsidian, editável, com diário e relatórios |
| Clima (OpenWeatherMap, cidade fixa) | Clima pelo Open-Meteo na cidade do usuário |
| Notícias | Notícias gerais e de tecnologia no briefing |
| Processos pesados, lixeira | Diagnóstico do PC + ações só com aprovação (processos, temporários, inicialização) |
| Gerador de código / debug | Claude Code: analisar, planejar e executar (com aprovação, sem commit) |
| Analisar tela por print | Anexos: imagens, PDF, Word, Excel e código, lidos pelo Claude |
| — | E-mail Gmail/Outlook, vagas, instalador, HUD, monitor de sessões do Claude Code |

## O que falta na Super Jarvis

Em ordem de valor para o seu uso:

1. **Abrir programas, sites e pastas por voz** ("abrir navegador, calculadora, Paint, Bloco de Notas, Word, Excel, CMD"). O Jarvis-AI procura o app no registro e nos atalhos do Menu Iniciar.
2. **Capturar a tela na hora** ("Jarvis, olha esse erro"). Hoje é preciso anexar o print à mão.
3. **Volume, brilho e "modo silêncio"** (silenciar e minimizar).
4. **Lembretes e timer/Pomodoro** ("me lembre às 15h de...").
5. **Energia: desligar, reiniciar ou suspender o PC**, com confirmação.
6. **Rotinas ou modos** que abrem ou fecham um conjunto de apps ("modo estudo", "modo gamer").
7. **Pequenas utilidades:** gerar senha forte, cotação de moedas, tocar música (busca no YouTube/Spotify), consertar a internet (diagnóstico de rede), ditado para arquivo.
8. **Controle pelo celular via Telegram** (mobile_bridge). É o item mais sensível: exige autorização forte por ID de chat.

## Cuidados ao implementar

- **Ações que mudam o estado do PC** (desligar, fechar apps, esvaziar lixeira) entram no fluxo **propor e aprovar** que já existe.
- **Abrir apps e sites** é de baixo risco, mas o pedido pode vir de um e-mail ou anexo malicioso. Por isso só abre o que **você** pediu, e sites só em `http(s)`.
- **O `action_handler_unsafe.py`** do Jarvis-AI executa comandos sem confirmação. Esse padrão **não** deve ser copiado.
