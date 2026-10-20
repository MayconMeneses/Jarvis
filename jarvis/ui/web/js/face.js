  // ── Tela FACE: overlay em tela cheia DENTRO da janela, com o mesmo orbe (modo "face") e painéis HUD reais. ──
  // Relógio (1 s), dados (3 s) e desenho do orbe só rodam com a FACE aberta E a janela visível.
  window.Face = (() => {
    const el = document.getElementById("face");
    if (!el) return null;
    const $ = (id) => document.getElementById(id);
    const TEXTO = { idle: "ONLINE", listening: "OUVINDO", thinking: "PROCESSANDO", speaking: "FALANDO" };
    let aberta = false, relogio = 0, dados = 0, emVoo = false, orbe = null, antes = null, telaCheia = false, legenda = "";

    const api = () => (window.pywebview && window.pywebview.api) || null;
    function tique() {
      const d = new Date();
      $("face-relogio").textContent = d.toLocaleTimeString("pt-BR", { hour12: false });
      $("face-data").textContent = d.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    }
    function estado() { $("face-estado").textContent = TEXTO[window.Orbe.s.estado] || "ONLINE"; }
    function desenharLegenda() { $("face-legenda").textContent = legenda; }
    async function atualizar() {
      if (emVoo || !aberta) return;
      emVoo = true;
      try {
        if (!api()) throw new Error("sem ponte");
        window.FacePaineis.desenhar(await api().face_dados());
      } catch (e) { window.FacePaineis.desenhar(null); } finally { emVoo = false; }
    }
    function ligarRelogios() {
      if (!aberta || document.hidden) return;
      if (!relogio) { tique(); relogio = setInterval(tique, 1000); }
      if (!dados) { atualizar(); dados = setInterval(atualizar, 3000); }
    }
    function pararRelogios() { clearInterval(relogio); clearInterval(dados); relogio = dados = 0; }

    function abrir() {
      if (aberta) return;
      aberta = true; antes = document.activeElement; el.hidden = false;
      if (!orbe) orbe = window.Orbe.montar($("face-orbe"), { modo: "face" });
      if (window.Orbe.principal) window.Orbe.principal.ativar(false);  // o orbe do topo fica escondido atrás: não desenha
      if (orbe) orbe.ativar(true);
      estado(); desenharLegenda(); ligarRelogios();
      $("face-fechar").focus();
    }
    function fechar() {
      if (!aberta) return;
      aberta = false; el.hidden = true; pararRelogios();
      if (orbe) orbe.ativar(false);
      if (window.Orbe.principal) window.Orbe.principal.ativar(true);
      if (telaCheia && api()) { api().face_tela_cheia(); telaCheia = false; }
      if (antes && antes.focus) antes.focus();
    }
    function digitando(alvo) {
      return !!alvo && (/^(INPUT|TEXTAREA|SELECT)$/.test(alvo.tagName) || alvo.isContentEditable);
    }
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && aberta) { ev.preventDefault(); fechar(); return; }
      if (aberta && ev.key === "Tab") {  // o foco fica dentro da FACE
        const f = [...el.querySelectorAll("button, input")].filter((x) => !x.disabled);
        const i = f.indexOf(document.activeElement);
        if (ev.shiftKey && i <= 0) { ev.preventDefault(); f[f.length - 1].focus(); }
        else if (!ev.shiftKey && i === f.length - 1) { ev.preventDefault(); f[0].focus(); }
        return;
      }
      if ((ev.key === "f" || ev.key === "F") && !ev.ctrlKey && !ev.altKey && !ev.metaKey && !digitando(ev.target)
          && !document.querySelector("dialog[open]")) {
        ev.preventDefault();
        if (aberta) fechar(); else abrir();
      }
    });
    document.addEventListener("visibilitychange", () => { if (document.hidden) pararRelogios(); else ligarRelogios(); });
    window.Orbe.aoMudar(() => { if (aberta) estado(); });
    const botao = $("open-face");
    if (botao) botao.addEventListener("click", abrir);
    $("face-fechar").addEventListener("click", fechar);
    $("face-cheia").addEventListener("click", async () => {
      try { if (api()) telaCheia = !!(await api().face_tela_cheia()); } catch (e) { telaCheia = false; }
    });
    $("face-auto").addEventListener("change", (ev) => { try { api().definir_face_ao_abrir(ev.target.checked); } catch (e) { /* sem ponte */ } });
    window.addEventListener("pywebviewready", async () => {
      try {
        const ligado = await api().face_ao_abrir();
        $("face-auto").checked = !!ligado;
        if (ligado) abrir();
      } catch (e) { /* sem ponte */ }
    });

    // Legenda: o que a Jarvis está dizendo (chamada por window.onVoice, em results.js). Texto puro, truncado.
    function falar(texto) {
      legenda = String(texto || "").replace(/\s+/g, " ").trim().slice(0, 400);
      if (aberta) desenharLegenda();
    }
    return { abrir, fechar, legenda: falar, aberta: () => aberta };
  })();
