  // ── Caixas arrastáveis (>= 1100 px): arrastar pelo título/alça, soltar em qualquer ponto da janela ────────────────
  // Funciona como mover uma pasta na área de trabalho. Mouse, toque e caneta via Pointer Events (setPointerCapture);
  // teclado na alça: Enter/Espaço pega e solta, setas movem (Shift = passo maior), Esc cancela. A caixa nunca sai da janela
  // nem fica sobre o orbe (zona proibida): ao soltar ali ela é empurrada para o lado livre mais próximo ou volta.
  // Abaixo de 1100 px o arrastar fica DESLIGADO de propósito (uma coluna só, o orbe ocupa a janela): as caixas voltam ao fluxo.
  // Caixa solta sai do fluxo e vai para a camada .camada-livre; um comentário no DOM guarda o lugar de origem.
  window.Arrastar = (() => {
    const palco = document.getElementById("principal"), L = typeof LayoutSalvo !== "undefined" ? LayoutSalvo : null;
    if (!palco || !L) return null;
    const $ = (id) => document.getElementById(id), api = () => (window.pywebview && window.pywebview.api) || null;
    const DEFS = {
      telemetria: () => palco.querySelector(".tele"), sessoes: () => $("fp-sessoes").closest(".painel"), uso: () => $("fp-uso").closest(".painel"),
      tarefas: () => $("fp-tarefas").closest(".painel"), emails: () => $("fp-emails").closest(".painel"), agentes: () => $("fp-status").closest(".painel"),
      canal: () => palco.querySelector(".canal"), clima: () => $("cx-clima"), vagas: () => $("cx-vagas"), noticias: () => $("cx-noticias"), tecnologia: () => $("cx-tecnologia"),
    };
    const largo = window.matchMedia("(min-width: 1100px)");
    const camada = document.createElement("div"); camada.className = "camada-livre"; palco.append(camada);
    const aviso = document.createElement("p"); aviso.className = "sr-only"; aviso.id = "arr-aviso"; aviso.setAttribute("role", "status"); aviso.setAttribute("aria-live", "polite"); document.body.append(aviso);
    const itens = {};  // id -> {id, el, marca, nome, grip, livre, pos:{x,y}, frac}
    let ativo = false, salvas = {}, sessao = null, pega = null, timerSalvar = 0, quadro = 0;

    const area = () => ({ w: palco.clientWidth, h: palco.clientHeight });
    const anunciar = (t) => { aviso.textContent = ""; setTimeout(() => { aviso.textContent = t; }, 30); };
    const suave = () => document.documentElement.dataset.efeitos === "completo" && !(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

    function zona() {  // retângulo (na área do palco) que cobre estado, orbe com ondas e botões de voz do centro
      const ar = palco.getBoundingClientRect(), centro = $("centro"), rs = [];
      for (const e of [palco.querySelector(".estado"), palco.querySelector(".orbe-linha"), $("escuta-linha"), $("foco-mic-caixa")]) {
        if (e && e.offsetParent) {
          const r = e.getBoundingClientRect(), largura = e.classList.contains("estado") ? Math.min(r.width, 260) : r.width;  // o texto de estado ocupa a coluna toda, mas só o miolo conta
          rs.push({ x: r.left - ar.left + (r.width - largura) / 2, y: r.top - ar.top + (centro ? centro.scrollTop : 0), w: largura, h: r.height });
        }
      }
      if (!rs.length) return null;
      const x0 = Math.min(...rs.map((r) => r.x)), y0 = Math.min(...rs.map((r) => r.y));
      return { x: x0, y: y0, w: Math.max(...rs.map((r) => r.x + r.w)) - x0, h: Math.max(...rs.map((r) => r.y + r.h)) - y0 };
    }
    const medida = (it) => ({ w: it.el.offsetWidth, h: it.el.offsetHeight });
    function por(it, x, y) {
      it.pos = { x, y }; it.el.style.transform = `translate3d(${x}px, ${y}px, 0)`;
      const z = zona();
      it.el.classList.toggle("arr-proibido", !!(z && L.cruza({ x, y, ...medida(it) }, z)));
    }
    function flutuar(it, x, y) {
      if (!it.livre) {
        const ar = palco.getBoundingClientRect(), r = it.el.getBoundingClientRect();
        if (x == null) { x = r.left - ar.left; y = r.top - ar.top; }
        it.el.classList.add("arr-livre"); camada.append(it.el); it.livre = true;
        if (it.id === "canal") $("log").scrollTop = $("log").scrollHeight;
      }
      if (x == null) { x = it.pos.x; y = it.pos.y; }  // já solta: só confere os limites
      const c = L.limitar({ x, y, ...medida(it) }, area()); por(it, c.x, c.y);
    }
    function devolver(it) {
      if (!it.livre) return;
      it.el.classList.remove("arr-livre", "arr-proibido", "arr-pegada", "arr-snap"); it.el.style.transform = "";
      it.marca.parentNode.insertBefore(it.el, it.marca); it.livre = false; it.pos = null;
      if (it.id === "canal") $("log").scrollTop = $("log").scrollHeight;
    }
    const resolverPos = (r) => L.resolver(r, area(), zona());
    function reposicionar() {  // janela mudou de tamanho (ou a caixa cresceu): a fração salva manda; fica dentro e fora do orbe
      if (!ativo || sessao || pega) return;
      for (const it of Object.values(itens)) {
        if (!it.livre || !it.frac) continue;
        const t = medida(it), r = L.paraPixels(it.frac, t, area()), res = resolverPos({ ...r, ...t });
        por(it, res.rejeitada ? r.x : res.x, res.rejeitada ? r.y : res.y);
      }
    }
    function agendarSalvar() {
      clearTimeout(timerSalvar);
      timerSalvar = setTimeout(async () => {
        try { if (api()) await api().set_layout(salvas); } catch (e) { anunciar("Não consegui salvar o layout; vale só nesta sessão."); }
      }, 300);
    }
    function guardar(it) { it.frac = L.dePixels({ ...it.pos, ...medida(it) }, area()); salvas[it.id] = { x: it.frac.x, y: it.frac.y }; agendarSalvar(); }

    // Fim do arrasto/teclado: resolve zona e limites, anima o encaixe (só com efeitos completos) e salva.
    function soltar(it, antes) {
      it.el.classList.remove("arr-pegada", "arr-proibido");
      const t = medida(it), res = resolverPos({ ...it.pos, ...t });
      if (res.rejeitada) { voltar(it, antes); anunciar(it.nome + ": não há lugar livre ali, voltou para onde estava."); return; }
      if (res.empurrada && suave()) { it.el.classList.add("arr-snap"); setTimeout(() => it.el.classList.remove("arr-snap"), 220); }
      por(it, res.x, res.y); guardar(it);
      anunciar(L.anuncio(it.nome, { ...it.pos, ...t }, area()) + (res.empurrada ? " Ajustada para ficar livre do orbe." : ""));
    }
    function voltar(it, antes) {
      it.el.classList.remove("arr-pegada", "arr-proibido");
      if (antes && antes.livre) por(it, antes.x, antes.y); else devolver(it);
    }
    const foto = (it) => ({ livre: it.livre, x: it.pos ? it.pos.x : 0, y: it.pos ? it.pos.y : 0 });

    // ── mouse, toque e caneta ──
    function aoPressionar(it, ev) {
      if (!ativo || pega || (ev.pointerType === "mouse" && ev.button !== 0)) return;
      const h = ev.target.closest(".arr-pega, .rot");
      if (!h || !it.el.contains(h) || (ev.target.closest("button") && !ev.target.closest(".arr-pega"))) return;
      sessao = { it, pid: ev.pointerId, h, x0: ev.clientX, y0: ev.clientY, moveu: false, antes: foto(it), dx: 0, dy: 0 };
      try { h.setPointerCapture(ev.pointerId); } catch (e) { /* alguns motores recusam */ }
    }
    function aoMover(ev) {
      if (!sessao || ev.pointerId !== sessao.pid) return;
      const s = sessao, it = s.it;
      if (!s.moveu) {
        if (Math.hypot(ev.clientX - s.x0, ev.clientY - s.y0) < 4) return;
        s.moveu = true; flutuar(it); it.el.classList.add("arr-pegada");
        try { s.h.setPointerCapture(s.pid); } catch (e) { /* mudar de pai solta a captura: pega de novo */ }
        const ar = palco.getBoundingClientRect(); s.dx = ev.clientX - ar.left - it.pos.x; s.dy = ev.clientY - ar.top - it.pos.y;
      }
      ev.preventDefault();
      const cx = ev.clientX, cy = ev.clientY;
      cancelAnimationFrame(quadro);
      quadro = requestAnimationFrame(() => { if (sessao === s) seguir(s, cx, cy); });
    }
    function seguir(s, cx, cy) {
      const ar = palco.getBoundingClientRect(), c = L.limitar({ x: cx - ar.left - s.dx, y: cy - ar.top - s.dy, ...medida(s.it) }, area());
      por(s.it, c.x, c.y);
    }
    function aoSoltar(ev, cancelar) {
      if (!sessao || ev.pointerId !== sessao.pid) return;
      const s = sessao; sessao = null; cancelAnimationFrame(quadro);
      try { s.h.releasePointerCapture(s.pid); } catch (e) { /* já solto */ }
      if (!s.moveu) return;
      if (!cancelar) seguir(s, ev.clientX, ev.clientY);  // o último movimento pode ainda estar na fila do quadro
      if (cancelar) voltar(s.it, s.antes); else soltar(s.it, s.antes);
    }

    // ── teclado (alça) ──
    function teclado(it, ev) {
      if (!ativo) return;
      const k = ev.key;
      if (k === "Enter" || k === " ") {
        ev.preventDefault();
        if (!pega) {
          pega = { it, antes: foto(it) }; flutuar(it); it.el.classList.add("arr-pegada"); it.grip.setAttribute("aria-pressed", "true");
          it.grip.focus({ preventScroll: true });  // mudar de pai tira o foco da alça
          anunciar(it.nome + " pega. Setas movem, Shift com setas move mais, Enter solta, Esc cancela.");
        } else fimTeclado(false);
      } else if (pega && pega.it === it && k === "Escape") { ev.preventDefault(); ev.stopPropagation(); fimTeclado(true); }
      else if (pega && pega.it === it) {
        const p = L.passo(k, ev.shiftKey);
        if (!p) return;
        ev.preventDefault();
        const c = L.limitar({ x: it.pos.x + p.dx, y: it.pos.y + p.dy, ...medida(it) }, area()); por(it, c.x, c.y);
        anunciar(L.anuncio(it.nome, { ...c, ...medida(it) }, area()));
      }
    }
    function fimTeclado(cancelar) {
      if (!pega) return;
      const { it, antes } = pega; pega = null; it.grip.setAttribute("aria-pressed", "false");
      if (cancelar) { voltar(it, antes); anunciar(it.nome + ": movimento cancelado."); } else soltar(it, antes);
      it.grip.focus({ preventScroll: true });
    }

    // ── montagem ──
    function montar(id) {
      const el = DEFS[id](); if (!el) return null;
      const rot = el.querySelector(".rot"), nome = rot ? rot.textContent.trim() : id, marca = document.createComment("origem " + id);
      el.parentNode.insertBefore(marca, el);
      const grip = document.createElement("button"); grip.type = "button"; grip.className = "arr-pega"; grip.textContent = "⠿"; grip.hidden = true;
      grip.setAttribute("aria-pressed", "false"); grip.setAttribute("aria-label", "Mover caixa " + nome + ". Enter para pegar");
      grip.title = "Arraste, ou use Enter e as setas";
      el.append(grip);
      const it = { id, el, marca, nome, grip, livre: false, pos: null, frac: null };
      el.addEventListener("pointerdown", (ev) => aoPressionar(it, ev));
      el.addEventListener("pointermove", aoMover);
      el.addEventListener("pointerup", (ev) => aoSoltar(ev, false));
      el.addEventListener("pointercancel", (ev) => aoSoltar(ev, true));
      grip.addEventListener("keydown", (ev) => teclado(it, ev));
      grip.addEventListener("blur", () => setTimeout(() => { if (pega && pega.it === it && document.activeElement !== grip) fimTeclado(true); }, 0));  // sair da alça cancela (mudar de pai não conta)
      return it;
    }
    function aplicarSalvas() {
      if (!ativo) return;
      for (const [id, f] of Object.entries(salvas)) {
        const it = itens[id]; if (!it) continue;
        if (!it.livre) flutuar(it, 0, 0);
        it.frac = f;
      }
      reposicionar();
    }
    function ligar() {
      ativo = largo.matches;
      document.body.classList.toggle("arr-ativo", ativo);
      for (const it of Object.values(itens)) {
        it.grip.hidden = !ativo;
        if (!ativo) { if (pega && pega.it === it) { pega = null; it.grip.setAttribute("aria-pressed", "false"); } devolver(it); }
      }
      if (ativo) aplicarSalvas();
    }
    function restaurarPadrao() {
      pega = null; sessao = null;
      for (const it of Object.values(itens)) { devolver(it); it.frac = null; it.grip.setAttribute("aria-pressed", "false"); }
      salvas = {}; clearTimeout(timerSalvar);
      (async () => { try { if (api()) await api().restaurar_layout(); } catch (e) { /* sem ponte */ } })();
      anunciar("Layout padrão restaurado.");
    }
    async function carregar() {
      try { salvas = L.sanear((await api().get_layout()).posicoes); } catch (e) { salvas = {}; }
      aplicarSalvas();
    }

    for (const id of L.IDS) { const it = DEFS[id] && montar(id); if (it) itens[id] = it; }
    const botao = $("layout-padrao"); if (botao) botao.addEventListener("click", restaurarPadrao);
    if (largo.addEventListener) largo.addEventListener("change", ligar);
    if (window.ResizeObserver) { const ro = new ResizeObserver(() => { cancelAnimationFrame(quadro); quadro = requestAnimationFrame(reposicionar); }); ro.observe(palco); const c = $("centro"); if (c) ro.observe(c); }
    window.addEventListener("pywebviewready", carregar);
    ligar();
    return { restaurarPadrao, aplicarSalvas, itens, ativo: () => ativo };
  })();
