  // ── Painéis laterais com dados reais + MODO FOCO (a antiga tela FACE, agora dentro do mesmo layout e do mesmo orbe) ──
  // Dados (3 s) só rodam com a janela visível e os painéis à mostra (>= 1100 px) ou no modo foco; o relógio, só no foco.
  // Modo foco: body.foco esconde as laterais, o canal e as caixas; o orbe cresce. Tecla F alterna, Esc sai, tela cheia é opcional.
  window.Face = (() => {
    const $ = (id) => document.getElementById(id);
    const barra = $("foco-barra");
    if (!barra) return null;
    const largo = window.matchMedia ? window.matchMedia("(min-width: 1100px)") : { matches: false, addEventListener() {} };
    let foco = false, relogio = 0, dados = 0, emVoo = false, antes = null, telaCheia = false, legenda = "";

    const api = () => (window.pywebview && window.pywebview.api) || null;
    function tique() {
      const d = new Date();
      $("face-relogio").textContent = d.toLocaleTimeString("pt-BR", { hour12: false });
      $("face-data").textContent = d.toLocaleDateString("pt-BR", { weekday: "long", day: "numeric", month: "long" });
    }
    async function atualizar() {
      if (emVoo || document.hidden) return;
      emVoo = true;
      try {
        if (!api()) throw new Error("sem ponte");
        const d = await api().face_dados();
        try { d.uso = await api().info_uso(); } catch (e) { d.uso = null; }
        window.FacePaineis.desenhar(d);
      } catch (e) { window.FacePaineis.desenhar(null); } finally { emVoo = false; }
    }
    const painelsVisiveis = () => largo.matches && !foco;
    function ligar() {
      clearInterval(relogio); clearInterval(dados); relogio = dados = 0;
      if (document.hidden) return;
      if (foco) { tique(); relogio = setInterval(tique, 1000); }
      if (painelsVisiveis()) { atualizar(); dados = setInterval(atualizar, 3000); }
    }

    function abrir() {
      if (foco) return;
      foco = true; antes = document.activeElement;
      document.body.classList.add("foco"); barra.hidden = false;
      $("face-legenda").textContent = legenda;
      ligar();
      if (window.FocoMic) window.FocoMic.entrar();
      $("face-fechar").focus();
    }
    function fechar() {
      if (!foco) return;
      foco = false; document.body.classList.remove("foco"); barra.hidden = true;
      if (telaCheia && api()) { api().face_tela_cheia(); telaCheia = false; }
      if (window.FocoMic) window.FocoMic.sair();
      ligar();
      if (antes && antes.focus && antes.offsetParent) antes.focus(); else $("tb-mais-btn").focus();
    }
    const digitando = (a) => !!a && (/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName) || a.isContentEditable);
    document.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape" && foco && !document.querySelector("dialog[open]") && $("tb-mais-menu").hidden) { ev.preventDefault(); fechar(); return; }
      if ((ev.key === "f" || ev.key === "F") && !ev.ctrlKey && !ev.altKey && !ev.metaKey && !digitando(ev.target) && !document.querySelector("dialog[open]")) {
        ev.preventDefault();
        if (foco) fechar(); else abrir();
      }
    });
    document.addEventListener("visibilitychange", ligar);
    if (largo.addEventListener) largo.addEventListener("change", ligar);
    const botao = $("open-face");
    if (botao) botao.addEventListener("click", abrir);
    $("face-fechar").addEventListener("click", fechar);
    $("face-cheia").addEventListener("click", async () => {
      try { if (api()) telaCheia = !!(await api().face_tela_cheia()); } catch (e) { telaCheia = false; }
    });
    $("face-auto").addEventListener("change", (ev) => { try { api().definir_face_ao_abrir(ev.target.checked); } catch (e) { /* sem ponte */ } });
    window.addEventListener("pywebviewready", async () => {
      ligar();
      try {
        const ligado = await api().face_ao_abrir();
        $("face-auto").checked = !!ligado;
        if (ligado) abrir();
      } catch (e) { /* sem ponte */ }
    });
    ligar();

    // Legenda: o que a Jarvis está dizendo (chamada por window.onVoice, em results.js). Texto puro, truncado.
    function falar(texto) {
      legenda = String(texto || "").replace(/\s+/g, " ").trim().slice(0, 400);
      if (foco) $("face-legenda").textContent = legenda;
    }
    return { abrir, fechar, legenda: falar, aberta: () => foco };
  })();
