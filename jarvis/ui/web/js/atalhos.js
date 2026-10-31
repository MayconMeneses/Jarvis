  // ── Botões no chat: opções do "Você quis dizer" (+ pesquisar na internet) e atalhos do fim do modo sem cérebro ──
  function grupoDeBotoes(rotulo) {
    const g = document.createElement("div");
    g.className = "opcoes"; g.setAttribute("role", "group"); g.setAttribute("aria-label", rotulo);
    return g;
  }

  function botaoDeChat(texto, aoClicar) {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = texto;
    b.addEventListener("click", aoClicar);
    return b;
  }

  function addOpcoes(texto, pedido) {
    const lista = Opcoes.extrair(texto);
    if (!lista.length) return;
    const g = grupoDeBotoes("Você quis dizer: escolha uma opção");
    const enviar = (eco, envio) => { g.remove(); add("user", eco); ask(envio, false); };  // mesmo caminho do "1", "2", "3" digitado
    lista.forEach((o) => g.appendChild(botaoDeChat(`${o.n}. ${o.rotulo}`, () => enviar(o.rotulo, String(o.n)))));
    const busca = Opcoes.pesquisa(pedido);
    if (busca) { const p = botaoDeChat("Pesquisar na internet", () => enviar("Pesquisar na internet", busca)); p.classList.add("ghost"); g.appendChild(p); }
    const nao = botaoDeChat("Nenhuma", () => enviar("Nenhuma delas", "não")); nao.classList.add("ghost"); g.appendChild(nao);
    log.appendChild(g);
    scrollDown();
    setTimeout(() => { if (g.isConnected) g.querySelector("button").focus({ preventScroll: true }); }, 50);  // depois de o composer devolver o foco ao campo
  }

  function addAtalhos(lista) {
    const itens = Opcoes.atalhos(lista);
    if (!itens.length) return;
    const g = grupoDeBotoes("Atalhos para ligar um cérebro");
    itens.forEach((a) => g.appendChild(botaoDeChat(a.rotulo, () => {
      if (a.tipo === "acao") document.getElementById("open-brains").click();
      else window.pywebview.api.open_link(a.alvo);
    })));
    log.appendChild(g);
    scrollDown();
  }

  // Cartões de aprovação devolvidos por pedidos feitos em diálogos (perfil, ferramentas): aparecem no chat, nada executa sozinho.
  function mostrarCartoes(cartoes) {
    (cartoes || []).forEach(addActionCard);
  }
