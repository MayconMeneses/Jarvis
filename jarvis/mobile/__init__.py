"""Jarvis no celular (iPhone, Android ou qualquer navegador): um app web instalável (PWA) que conversa com a Jarvis do PC.

- servidor.py: servidor HTTP pequeno dentro da Jarvis (desligado por padrão; só na rede local ou em Tailscale).
- pareamento.py: código de 6 dígitos mostrado na janela do PC troca por um token do aparelho (guardado só como hash).
- icones.py: ícones PNG gerados na hora.
- web/: a tela do celular (HTML, CSS, JS, manifesto e service worker).

Segurança: o celular só CONVERSA; ações que mudam o PC continuam aparecendo como cartão e só valem aprovadas na janela do PC.
"""
