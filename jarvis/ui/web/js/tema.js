  // ── tema e fundo de aurora ───────────────────────────────────────────
  // O tema já vem no <html data-tema> (page(cfg)); aqui só a troca pelo seletor do diálogo Cérebros.
  // "Efeitos" é um controle só (Orbe.definirModo), que também grava data-efeitos no <html>.
  (() => {
    const raiz = document.documentElement, sel = document.getElementById("tema");
    const aplicar = (tema) => {
      raiz.dataset.tema = tema;
      if (sel) sel.value = tema;
      window.dispatchEvent(new Event("jarvis-tema"));
    };
    // Janela oculta (bandeja/minimizada): pausa a aurora.
    const visivel = () => { if (document.hidden) raiz.dataset.oculta = "1"; else delete raiz.dataset.oculta; };
    document.addEventListener("visibilitychange", visivel);
    visivel();
    if (sel) {
      sel.value = raiz.dataset.tema || "hud";
      sel.addEventListener("change", async () => {
        const antes = raiz.dataset.tema, fb = document.getElementById("fb-tema");
        aplicar(sel.value);
        try {
          const res = await window.pywebview.api.set_tema(sel.value);
          if (!res.ok) aplicar(res.tema || antes);
          fb.textContent = res.mensagem; fb.className = "feedback " + (res.ok ? "on-ok" : "on-no");
        } catch (e) { fb.textContent = "Tema trocado só nesta sessão."; fb.className = "feedback on-no"; }
      });
    }
    window.addEventListener("pywebviewready", async () => {
      try { aplicar((await window.pywebview.api.get_tema()).tema); } catch (e) { /* sem ponte */ }
    });
  })();
