  // ── Ferramentas externas (MCP) no ⚙ Cérebros: lista o catálogo curado e só PEDE instalar/desativar/remover (cartão de aprovação). ──
  (() => {
    const $ = (id) => document.getElementById(id);
    const api = () => (window.pywebview && window.pywebview.api) || null;
    const RISCO = { baixo: "risco baixo", medio: "risco médio", alto: "risco alto" };
    const dizer = (texto, ok) => { const e = $("ft-info"); e.textContent = texto || ""; e.className = "feedback " + (ok ? "on-ok" : "on-no"); };
    const no = (tag, texto, cls) => { const e = document.createElement(tag); if (texto != null) e.textContent = texto; if (cls) e.className = cls; return e; };

    function botao(rotulo, acao, item, classe) {
      const b = no("button", rotulo, classe);
      b.type = "button"; b.setAttribute("aria-label", `${rotulo} ${item.nome}`);
      b.addEventListener("click", () => pedir(acao, item, b));
      return b;
    }

    function cartao(item) {
      const li = no("li", null, "ft-item");
      const estado = item.ativa ? "ativa" : item.instalada ? "instalada, desativada" : "não instalada";
      const h = no("h4");
      h.append(no("span", `${item.nome} v${item.versao}`), no("span", `${estado} · ${RISCO[item.risco] || "risco " + item.risco}`, "ft-risco-" + item.risco));
      li.append(h, no("p", item.descricao));
      const permissoes = no("ul"); permissoes.setAttribute("aria-label", "Permissões de " + item.nome);
      (item.permissoes || []).forEach((p) => permissoes.appendChild(no("li", "Permissão: " + p)));
      const riscos = no("ul"); riscos.setAttribute("aria-label", "Riscos de " + item.nome);
      (item.riscos || []).forEach((r) => riscos.appendChild(no("li", "Risco: " + r)));
      const botoes = no("div", null, "ft-botoes");
      if (!item.ativa) botoes.appendChild(botao("Instalar", "instalar", item, "primary"));
      if (item.ativa) botoes.appendChild(botao("Desativar", "desativar", item));
      if (item.instalada) botoes.appendChild(botao("Remover", "remover", item, "danger"));
      li.append(permissoes, riscos, botoes);
      return li;
    }

    async function pedir(acao, item, b) {
      const ponte = api();
      if (!ponte) return;
      b.disabled = true;
      let res;
      try { res = await ponte.ferramenta_externa_pedir(acao, item.id); } catch (e) { res = { ok: false, mensagem: "Não consegui falar com a Jarvis agora." }; }
      b.disabled = false;
      if (!res.ok) return dizer(res.mensagem || "Não foi possível preparar o pedido.", false);
      $("brains").close();
      mostrarCartoes(res.acoes);
      add("jarvis", res.mensagem, "ferramentas");
    }

    async function carregar() {
      const lista = $("ft-lista"), ponte = api();
      if (!ponte) return;
      lista.setAttribute("aria-busy", "true");
      let itens = null;
      try { itens = await ponte.ferramentas_externas(); } catch (e) { itens = null; }
      lista.setAttribute("aria-busy", "false");
      lista.replaceChildren();
      if (!Array.isArray(itens)) return dizer("Não consegui ler o catálogo de ferramentas agora.", false);
      dizer("", true);
      $("ft-contagem").textContent = itens.length ? `${itens.filter((i) => i.ativa).length} de ${itens.length} ativas` : "";
      if (!itens.length) lista.appendChild(no("li", "O catálogo está vazio.", "ft-item"));
      itens.forEach((i) => lista.appendChild(cartao(i)));
    }
    $("open-brains").addEventListener("click", carregar);
  })();
