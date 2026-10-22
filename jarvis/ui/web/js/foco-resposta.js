  // ── Resposta no modo foco: legenda curta + painel rolável "Ver mais", em Markdown formatado (md.js, só DOM) ──────────
  // A resposta nunca estoura a tela: curta cabe na legenda; longa mostra só o começo e abre num painel com rolagem interna.
  // Leitor de tela: o texto sem marcação é anunciado numa região aria-live; Esc recolhe o painel antes de sair do foco.
  window.FocoResposta = (() => {
    const $ = (id) => document.getElementById(id);
    const caixa = $("foco-resp"), leg = $("face-legenda"), painel = $("foco-resp-painel"), mais = $("foco-resp-mais"), anuncio = $("foco-resp-anuncio");
    if (!caixa || !leg || !painel || !mais || !window.Md) return null;
    const MAX_LEGENDA = 140, MAX_TEXTO = 6000;
    let texto = "", aberto = false;

    function pintar() {
      caixa.hidden = !texto;
      const curta = Md.simples(texto, MAX_LEGENDA);
      if (curta) Md.render(leg, texto); else leg.textContent = Md.resumo(texto, MAX_LEGENDA).texto;
      leg.hidden = aberto;
      painel.hidden = !aberto;
      if (aberto) Md.render(painel, texto);
      mais.hidden = curta;
      mais.textContent = aberto ? "Ver menos" : "Ver mais";
      mais.setAttribute("aria-expanded", String(aberto));
    }
    function definir(sim) {
      if (aberto === !!sim) return;
      aberto = !!sim; pintar();
      if (aberto) painel.scrollTop = 0;
    }
    function mostrar(novo) {
      texto = String(novo || "").trim().slice(0, MAX_TEXTO);
      aberto = false; painel.scrollTop = 0; pintar();
      anuncio.textContent = texto ? Md.resumo(texto, 300).texto : "";
    }
    mais.addEventListener("click", () => definir(!aberto));
    return { mostrar, recolher: () => definir(false), aberta: () => aberto, texto: () => texto };
  })();
