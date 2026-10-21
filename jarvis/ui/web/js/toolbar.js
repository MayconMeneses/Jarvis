  // ── menu ☰: abre/fecha, setas, Home/End, letra inicial, Esc devolve o foco, tecla M abre ─────────────────
  (() => {
    const btn = document.getElementById("tb-mais-btn"), menu = document.getElementById("tb-mais-menu");
    if (!btn || !menu) return;
    const itens = () => [...menu.querySelectorAll('[role="menuitem"], select')].filter((e) => !e.disabled);
    const aberto = () => !menu.hidden;

    function fechar(devolverFoco) {
      if (!aberto()) return;
      menu.hidden = true; btn.setAttribute("aria-expanded", "false");
      if (devolverFoco) btn.focus();
    }
    function abrir(foco) {
      menu.hidden = false; btn.setAttribute("aria-expanded", "true");
      const l = itens();
      if (foco === "fim") l[l.length - 1].focus(); else if (foco === "inicio") l[0].focus();
    }
    btn.addEventListener("click", (ev) => (aberto() ? fechar(false) : abrir(ev.detail === 0 ? "inicio" : undefined)));  // detail 0 = teclado: já entra no menu
    btn.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown") { ev.preventDefault(); abrir("inicio"); }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); abrir("fim"); }
    });
    menu.addEventListener("keydown", (ev) => {
      const l = itens(), i = l.indexOf(document.activeElement), noSelect = ev.target.tagName === "SELECT";
      if (ev.key === "Escape") fechar(true);
      else if (ev.key === "Tab") { fechar(false); return; }
      else if (noSelect && (ev.key.startsWith("Arrow") || ev.key === "Home" || ev.key === "End")) return;  // o seletor usa as setas dele
      else {
        let alvo = MenuNav.proximo(i, l.length, ev.key);
        if (alvo === null && ev.key.length === 1 && !ev.ctrlKey && !ev.altKey && !ev.metaKey) {
          alvo = MenuNav.porLetra(l.map((e) => e.textContent), i, ev.key);
          if (alvo < 0) return;
        }
        if (alvo === null) return;
        l[alvo].focus();
      }
      ev.preventDefault();
    });
    // Escolher um item fecha o menu (o clique do item já fez a sua ação). Clique fora também fecha.
    menu.addEventListener("click", (ev) => { if (ev.target.closest('[role="menuitem"]')) fechar(false); });
    document.addEventListener("click", (ev) => { if (aberto() && !ev.target.closest(".tb-mais")) fechar(false); });
    // Tecla M abre o menu (fora de campos de texto e com nenhum diálogo aberto).
    document.addEventListener("keydown", (ev) => {
      if ((ev.key !== "m" && ev.key !== "M") || ev.ctrlKey || ev.altKey || ev.metaKey || ev.defaultPrevented) return;
      const a = ev.target;
      if (a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable) || document.querySelector("dialog[open]")) return;
      ev.preventDefault();
      if (aberto()) fechar(true); else { abrir("inicio"); }
    });
    // Menu fechado esconde o item que abriu o diálogo: ao fechar o diálogo, o foco volta para o botão ☰.
    document.addEventListener("close", (ev) => {
      if (!(ev.target instanceof HTMLDialogElement)) return;
      setTimeout(() => { const a = document.activeElement; if ((!a || a === document.body || !a.offsetParent) && btn.offsetParent) btn.focus(); }, 0);
    }, true);
  })();
