// Temas visuais (data-tema no <html>) e o eixo Efeitos. As cores ficam em css/tema.css; aqui só a lista, a escolha guardada e a aplicação.
// Efeitos usa a MESMA chave do orbe (meta "orbe_modo"): "completo" liga o orbe animado e o fundo de aurora; "suave" e "desligado" cortam os dois.
export const TEMAS = [
  { id: "hud", rotulo: "HUD (padrão)", barra: "#040a14" },
  { id: "ambar", rotulo: "Âmbar", barra: "#0c0803" },
  { id: "esmeralda", rotulo: "Esmeralda", barra: "#03100b" },
  { id: "contraste", rotulo: "Alto contraste", barra: "#000000" },
];
export const temaValido = (id) => (TEMAS.some((t) => t.id === id) ? id : "hud");

// Aplica no <html> (e na cor da barra do navegador). `doc` é injetável para teste.
export function aplicarTema(id, doc = document) {
  const tema = TEMAS.find((t) => t.id === temaValido(id));
  doc.documentElement.setAttribute("data-tema", tema.id);
  doc.querySelector('meta[name="theme-color"]')?.setAttribute("content", tema.barra);
  return tema.id;
}

export async function lerTema(memoria) {
  try { return temaValido(await memoria.meta("tema")); } catch { return "hud"; }
}
export async function guardarTema(memoria, id) {
  try { await memoria.definirMeta("tema", temaValido(id)); } catch { /* sem armazenamento: vale só nesta sessão */ }
}

// Efeitos efetivos ("completo" | "suave" | "desligado") no <html>; o CSS decide o que mostrar (aurora só em completo).
export function aplicarEfeitos(modo, doc = document) { doc.documentElement.setAttribute("data-efeitos", modo); }

// A aurora para sozinha quando a aba fica oculta.
export function vigiarAba(doc = document) {
  const marcar = () => { if (doc.hidden) doc.documentElement.setAttribute("data-oculto", ""); else doc.documentElement.removeAttribute("data-oculto"); };
  doc.addEventListener("visibilitychange", marcar);
  marcar();
}
