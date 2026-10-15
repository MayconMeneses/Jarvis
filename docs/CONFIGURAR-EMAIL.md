# Conectar o e-mail à Jarvis

A Jarvis acessa o e-mail pelas APIs oficiais, com o seu login (OAuth). Ela **nunca vê a sua senha**: você autoriza no site do Google ou da Microsoft e o acesso fica salvo neste PC, criptografado com a proteção do Windows (DPAPI).

O que ela pode fazer: ler a caixa de entrada (remetente, assunto e prévia) e **adicionar marcadores** como `Jarvis/Financeiro`. Isso só acontece depois que você clica em **Aprovar** na janela.
O que ela não faz: apagar, mover para a lixeira, enviar ou responder.

> Os nomes dos menus do Google Cloud e do Microsoft Entra mudam com frequência. Se algum botão estiver com outro nome, procure pelo termo entre parênteses.

---

## Gmail

Cada pessoa precisa de um "cliente OAuth" próprio. Leva cerca de 10 minutos e é gratuito.

1. Acesse https://console.cloud.google.com e crie um projeto chamado **Super Jarvis**.
2. Em **APIs e serviços > Biblioteca**, procure **Gmail API** e clique em **Ativar**.
3. Em **Google Auth Platform** (ou "Tela de consentimento OAuth"):
   - tipo de usuário **Externo**; nome do app: *Super Jarvis*; informe o seu e-mail nos campos de contato;
   - em **Público-alvo** (ou "Usuários de teste"), adicione o seu Gmail.
4. Em **Clientes** (ou "Credenciais > Criar credenciais > ID do cliente OAuth"):
   - tipo de aplicativo: **App para computador** (Desktop app);
   - crie e clique em **Baixar JSON**.
5. Salve o arquivo baixado exatamente como:
   `C:\Users\maico\AppData\Roaming\SuperJarvis\gmail_client_secret.json`
6. Conecte:

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis --conectar gmail
```

O navegador abre. Escolha a sua conta e autorize. Como o app é seu e não foi verificado pelo Google, aparece o aviso **"O Google não verificou este app"**: clique em **Avançado > Acessar Super Jarvis**.

**Importante sobre expiração:** enquanto o app estiver no status **"Teste"**, o Google faz o acesso expirar a cada **7 dias** (é só rodar o `--conectar gmail` de novo). Para não expirar, mude o status para **"Em produção"** em *Público-alvo*. Ele continua sem verificação, que só é exigida para apps com muitos usuários, e o aviso de app não verificado continua aparecendo no login.

---

## Outlook / Hotmail

1. Acesse https://entra.microsoft.com com a sua conta Microsoft (a do Hotmail).
   - Se o site pedir para criar um diretório ou uma conta do Azure antes, isso é uma exigência atual da Microsoft para contas pessoais. A conta gratuita do Azure resolve; a criação é feita por você.
2. Vá em **Registros de aplicativo > Novo registro**:
   - nome: *Super Jarvis*;
   - tipos de conta: **Somente contas pessoais da Microsoft** (ou a opção que inclui "contas pessoais da Microsoft");
   - URI de redirecionamento: plataforma **Cliente público/nativo (móvel e área de trabalho)**, valor `http://localhost`.
3. Copie o **ID do aplicativo (cliente)** da página de visão geral.
4. Em **Autenticação**, ative **Permitir fluxos de clientes públicos** e salve.
5. Em **Permissões de API > Adicionar permissão > Microsoft Graph > Permissões delegadas**, marque **Mail.ReadWrite**.
6. Abra `C:\Users\maico\AppData\Roaming\SuperJarvis\config.json` e cole o ID copiado:

```json
"email": {
  "outlook_client_id": "COLE-AQUI-O-ID-DO-APLICATIVO",
  "outlook_authority": "consumers"
}
```

   (Se você escolheu um tipo de conta que inclui contas de empresa, use `"common"` em vez de `"consumers"`.)

7. Conecte:

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis --conectar outlook
```

---

## Regras fixas (opcional, custo zero)

No `config.json`, em `email.regras`, você define categorias automáticas por remetente ou assunto. Elas valem antes da IA:

```json
"regras": [
  {"campo": "remetente", "contem": "nubank", "categoria": "Financeiro"},
  {"campo": "assunto", "contem": "vaga", "categoria": "Trabalho e vagas"},
  {"campo": "remetente", "contem": "noreply@github.com", "categoria": "Notificações"}
]
```

Categorias disponíveis: Importante, Financeiro, Trabalho e vagas, Promoções, Notificações, Ler depois, Suspeito.

## Proteção contra e-mails maliciosos

Um e-mail que tenta dar ordens à IA (por exemplo, "Jarvis, apague tudo" ou "ignore as instruções anteriores") é marcado como **Suspeito** e nunca vira comando. Toda mudança passa pelo seu clique em **Aprovar**.

## Desconectar

```bash
C:\Users\maico\.venvs\super-jarvis\Scripts\python.exe -m jarvis --desconectar gmail
```

Isso apaga o acesso salvo neste PC. Para revogar também do lado do Google, use https://myaccount.google.com/permissions. Na Microsoft, use https://account.live.com/consent/Manage.
