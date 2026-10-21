// Teclado virtual do iPhone: o Safari não encolhe a página, só a "área visível". Medimos essa área e o app acompanha,
// para o campo de texto nunca ficar escondido. Com o teclado aberto, a barra de abas some (mais espaço para conversar).
export const LIMITE_TECLADO = 120;  // px: diferença mínima para considerar que é o teclado, não a barra do Safari

export function medirTeclado(visivel, janela) {
  const alt = Math.round(visivel?.height || janela.innerHeight);
  const topo = Math.round(visivel?.offsetTop || 0);
  return { altura: alt, topo, aberto: janela.innerHeight - alt > LIMITE_TECLADO };
}

export function ligarTeclado(janela = window, doc = document) {
  const vv = janela.visualViewport;
  if (!vv) return () => {};
  const raiz = doc.documentElement;
  const aplicar = () => {
    const m = medirTeclado(vv, janela);
    raiz.style.setProperty("--app-alt", m.aberto ? m.altura + "px" : "100dvh");
    raiz.toggleAttribute("data-teclado", m.aberto);
    if (m.aberto && m.topo) janela.scrollTo(0, 0);  // o Safari rola a página para achar o campo; o app já coube, então volta ao topo
  };
  vv.addEventListener("resize", aplicar);
  vv.addEventListener("scroll", aplicar);
  doc.addEventListener("focusin", (ev) => {
    if (ev.target.matches?.("textarea, input")) setTimeout(() => ev.target.scrollIntoView?.({ block: "center", behavior: "smooth" }), 300);
  });
  aplicar();
  return () => { vv.removeEventListener("resize", aplicar); vv.removeEventListener("scroll", aplicar); };
}
