# Jarvis no celular (iPhone 13 Pro Max e outros)

A Jarvis do celular é um **app web instalável (PWA)** que conversa com a Jarvis que roda no seu PC. Funciona no iPhone (Safari),
no Android (Chrome) e em qualquer navegador, sem App Store e sem conta de desenvolvedor.

## Como ligar

1. No PC, abra a janela da Jarvis → ⚙ **Cérebros** → ligue **Jarvis no celular**. Aparece o endereço, por exemplo `http://192.168.0.12:8765`.
2. No iPhone (no mesmo Wi-Fi), abra esse endereço no **Safari**.
3. No PC, toque em **Gerar código de pareamento**. No iPhone, digite o código de 6 dígitos (vale 5 minutos, uso único) e toque em **Conectar**.
4. Para virar app: no Safari, **Compartilhar → Adicionar à Tela de Início**. A Jarvis abre em tela cheia, com ícone próprio.

Dentro do app: conversa por texto, atalhos (Bom dia, PC, Pendências, Notícias, Treino), ditado por voz em português (🎤) e opção de ler as
respostas em voz alta. Para remover um aparelho (celular perdido), use **Remover** na lista do mesmo painel: ele perde o acesso na hora.

## Segurança

- Desligado por padrão. Só responde a aparelhos pareados (token guardado como hash; código de uso único; 5 erros bloqueiam por 5 minutos).
- O celular **só conversa**. Ações que mudam o PC (apagar, instalar, criar projeto, enviar e-mail) continuam sendo cartões que **você aprova na
  janela do PC**; o app só avisa "N ações esperando".
- Em HTTP puro, o tráfego na rede Wi-Fi não é criptografado. Use só em rede de casa. Para usar fora de casa com criptografia, instale o
  **Tailscale** no PC e no iPhone (grátis para uso pessoal), gere o certificado (`tailscale cert`) e informe os caminhos em
  `celular_certificado` e `celular_chave` no `config.json`; o endereço passa a ser `https://`. Nunca exponha a porta na internet pública.

## Limites desta versão

- O celular **depende do PC ligado** e na mesma rede (ou no Tailscale): o modelo de linguagem e as ferramentas rodam no PC.
- Não é um app nativo da App Store. Um app nativo exige um Mac com Xcode e uma conta Apple Developer (US$ 99 por ano); só vale a pena se
  você precisar de notificações push nativas ou de rodar o modelo no próprio iPhone. Ficou como etapa futura.
- Service worker (abrir a casca do app sem rede) só funciona em HTTPS; em HTTP o app abre, mas precisa da rede para tudo.
- Aparelhos com mais memória e processador: no PC, a Jarvis escolhe o modelo local pelo tamanho da memória (1,5B até 8 GB, 3B a partir de
  12 GB, 7B a partir de 28 GB) com o comando "instalar cérebro local".
