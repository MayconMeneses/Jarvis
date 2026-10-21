  // ── Cartão do briefing no miolo do orbe: título curto, uma linha de detalhe e abas AGENDA / E-MAILS / NOTÍCIAS ──
  // Dados de info_briefing() (somente leitura, sem IA, sem falar). Tudo entra por textContent: título de evento e
  // assunto de e-mail são dado de terceiros. As regras de texto são puras (testáveis no Node).
  const BriefingRegras = (() => {
    const plural = (n, um, varios) => (n === 1 ? um : varios);
    function titulo(d) {
      if (!d) return "Sem dados agora";
      const itens = ((d.agenda && d.agenda.total) || 0) + ((d.emails && d.emails.total) || 0);
      if (!d.agenda && !d.emails && !d.noticias) return "Conecte agenda e e-mail";
      return itens === 0 ? "Sem desvios relevantes" : `${itens} ${plural(itens, "item pede", "itens pedem")} atenção`;
    }
    function linha(d, aba) {
      const x = d && d[aba];
      if (aba === "agenda") {
        if (!x) return "Agenda não conectada. Conecte pelo menu.";
        return x.total === 0 ? "Nenhum compromisso hoje." : `${x.total} ${plural(x.total, "compromisso", "compromissos")} hoje: ${x.itens.join(" · ")}`;
      }
      if (aba === "emails") {
        if (!x) return "E-mail não conectado ou sem leitura agora.";
        return x.total === 0 ? "Nenhum e-mail não lido." : `${x.total} ${plural(x.total, "não lido", "não lidos")}: ${x.itens.join(" · ")}`;
      }
      if (!x) return "Manchetes carregando…";
      return x.total === 0 ? "Sem manchetes agora." : x.itens[0];
    }
    return { titulo, linha };
  })();
  if (typeof module !== "undefined") module.exports = BriefingRegras;

  if (typeof window !== "undefined") window.Briefing = (typeof document === "undefined" || !document.getElementById("briefing")) ? null : (() => {
    const $ = (id) => document.getElementById(id), caixa = $("briefing"), abas = [...caixa.querySelectorAll('[role="tab"]')];
    let dados = null, aba = "agenda", emVoo = false;

    function desenhar() {
      $("br-titulo").textContent = BriefingRegras.titulo(dados);
      $("br-linha").textContent = BriefingRegras.linha(dados, aba);
      abas.forEach((b) => { const on = b.dataset.aba === aba; b.setAttribute("aria-selected", on ? "true" : "false"); b.tabIndex = on ? 0 : -1; });
    }
    async function atualizar() {
      const ponte = window.pywebview && window.pywebview.api;
      if (emVoo || !ponte || !ponte.info_briefing) return;
      emVoo = true;
      const antes = dados && dados.noticias;  // as manchetes vêm das caixas: não perde ao reler agenda e e-mails
      try { dados = await ponte.info_briefing(); } catch (e) { dados = null; }
      if (dados && !dados.noticias && antes) dados.noticias = antes;
      emVoo = false;
      caixa.setAttribute("aria-busy", "false"); desenhar();
    }
    function escolher(b, foco) { aba = b.dataset.aba; desenhar(); if (foco) b.focus(); }
    abas.forEach((b, i) => {
      b.addEventListener("click", () => escolher(b, false));
      b.addEventListener("keydown", (ev) => {
        const j = ev.key === "ArrowRight" ? (i + 1) % abas.length : ev.key === "ArrowLeft" ? (i + abas.length - 1) % abas.length : ev.key === "Home" ? 0 : ev.key === "End" ? abas.length - 1 : -1;
        if (j >= 0) { ev.preventDefault(); escolher(abas[j], true); }
      });
    });
    // As manchetes das caixas alimentam a aba Notícias sem repetir a busca.
    function noticias(itens) {
      const lista = (itens || []).map((i) => i.titulo);
      dados = Object.assign({}, dados || { ok: true, agenda: null, emails: null }, { noticias: { total: lista.length, itens: lista.slice(0, 3) } });
      desenhar();
    }
    desenhar();
    window.addEventListener("pywebviewready", atualizar);
    periodico(atualizar, 300000);
    return { atualizar, noticias };
  })();
