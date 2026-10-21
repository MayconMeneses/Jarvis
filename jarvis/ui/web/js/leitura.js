  // ── "Ler para mim": botão por item das caixas. Estados: ocioso, baixando, traduzindo, lendo, erro, original ──────────
  // A ponte (ler_item/parar_leitura/estado_leitura) faz tudo: detecta o idioma, traduz para pt-BR e fala. Aqui só se
  // mostra o estado real, com UMA leitura por vez. Nunca lê sozinha (só com clique) e o texto lido nunca vira ação.
  const LeituraRegras = (() => {
    // Estado devolvido pela ponte -> aparência do botão. `fim` = a leitura acabou (hora de parar de consultar).
    function visual(st) {
      const e = (st && st.estado) || "parado";
      if (e === "baixando") return { estado: "baixando", texto: "Baixando…", pressed: false, fim: false };
      if (e === "traduzindo") return { estado: "traduzindo", texto: "Traduzindo…", pressed: false, fim: false };
      if (e === "lendo") return { estado: "lendo", texto: "Parar leitura", pressed: true, fim: false };
      if (st && st.oferece_original) return { estado: "original", texto: "Ler no idioma original", pressed: false, fim: true };
      if (st && (st.ok === false || /^Não consegui/.test(st.mensagem || ""))) return { estado: "erro", texto: "Não consegui ler. Tentar de novo", pressed: false, fim: true };
      return { estado: "ocioso", texto: "Ler para mim", pressed: false, fim: true };
    }
    return { visual };
  })();
  if (typeof module !== "undefined") module.exports = LeituraRegras;

  if (typeof window !== "undefined") window.Leitura = (typeof document === "undefined") ? null : (() => {
    const api = () => (window.pywebview && window.pywebview.api) || null;
    let ativo = null, timer = 0, fezFala = false;

    function pintar(a, v, mensagem) {
      a.btn.dataset.estado = v.estado; a.btn.textContent = v.texto; a.btn.setAttribute("aria-pressed", v.pressed ? "true" : "false");
      a.btn.title = v.estado === "traduzindo" || v.estado === "baixando" ? "Clique para cancelar" : "";
      if (a.msg) a.msg.textContent = mensagem || (v.estado === "lendo" ? "Lendo em voz alta." : "");
    }
    function ocioso(a) { a.btn.dataset.estado = "ocioso"; a.btn.textContent = "Ler para mim"; a.btn.setAttribute("aria-pressed", "false"); a.btn.title = ""; }
    function orbe(lendo) {  // sem evento real da fala (voz desligada), o orbe ainda "fala" num ritmo simulado
      if (!window.Orbe) return;
      if (lendo && !fezFala && window.Orbe.s.estado !== "speaking") { fezFala = true; window.Orbe.evento({ tipo: "fala", env: [] }); }
      else if (!lendo && fezFala) { fezFala = false; window.Orbe.evento({ tipo: "fim" }); }
    }
    function terminar(v, st) {
      clearInterval(timer); timer = 0; orbe(false);
      if (!ativo) return;
      const a = ativo; ativo = null;
      pintar(a, v, v.estado === "erro" || v.estado === "original" ? (st && st.mensagem) || "" : "");
      if (v.estado === "ocioso" && a.msg) a.msg.textContent = st && st.mensagem === "Leitura concluída." ? "Leitura concluída." : "";
    }
    async function consultar() {
      if (!ativo || !api()) return;
      try {
        const st = await api().estado_leitura(), v = LeituraRegras.visual(st);
        if (!ativo) return;
        if (v.fim) { terminar(v, st); return; }
        orbe(v.estado === "lendo"); pintar(ativo, v, v.estado === "lendo" ? "" : String(st.mensagem || "").slice(0, 120));
      } catch (e) { terminar({ estado: "erro", texto: "Não consegui ler. Tentar de novo" }, { mensagem: "Sem resposta da Jarvis." }); }
    }
    async function parar() {
      if (!ativo) return;
      const a = ativo; terminar({ estado: "ocioso", texto: "Ler para mim", pressed: false, fim: true }, { mensagem: "" });
      if (a.msg) a.msg.textContent = "Leitura parada.";
      try { if (api()) await api().parar_leitura(); } catch (e) { /* sem ponte */ }
    }
    // Pedido: botão, mensagem de status da caixa e o item {tipo, titulo, trecho, url?}.
    async function alternar(btn, msg, item, extra) {
      if (ativo && ativo.btn === btn) { await parar(); return; }  // clicar de novo (ou durante a tradução) cancela
      if (ativo) { const a = ativo; terminar({ estado: "ocioso", texto: "Ler para mim", pressed: false, fim: true }, { mensagem: "" }); void a; }
      if (!api() || !api().ler_item) { msg.textContent = "A leitura em voz alta não está disponível nesta janela."; return; }
      ativo = { btn, msg };
      pintar(ativo, { estado: "traduzindo", texto: "Preparando…", pressed: false }, "");
      try {
        const st = await api().ler_item(Object.assign({}, item, extra || {})), v = LeituraRegras.visual(st);
        if (!ativo) return;
        if (st.ok === false) { terminar({ estado: "erro", texto: "Não consegui ler. Tentar de novo", fim: true }, st); return; }
        if (v.fim) { terminar(v, st); return; }
        pintar(ativo, v, ""); orbe(v.estado === "lendo");
        clearInterval(timer); timer = setInterval(consultar, 800);
      } catch (e) { terminar({ estado: "erro", texto: "Não consegui ler. Tentar de novo", fim: true }, { mensagem: "Sem resposta da Jarvis." }); }
    }
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && ativo && !document.querySelector("dialog[open]")) { ev.preventDefault(); parar(); }
    });
    return { alternar, parar, ativo: () => !!ativo, ocioso };
  })();
