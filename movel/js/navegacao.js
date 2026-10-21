// Barra de abas de baixo, no estilo de app: as 4 principais ficam à vista e o resto abre em "Mais" (alcance do polegar).
export const PRINCIPAIS = 4;

// Separa quais abas ficam na barra e quais vão para "Mais". Com uma só aba sobrando, ela cabe na barra (Mais seria pior).
export function dividirAbas(ids, max = PRINCIPAIS) {
  return ids.length <= max + 1 ? { barra: [...ids], mais: [] } : { barra: ids.slice(0, max), mais: ids.slice(max) };
}

export function ligarNavegacao(nav = document.getElementById("abas"), doc = document) {
  const botoes = [...nav.querySelectorAll("button[data-aba]")];
  const { mais } = dividirAbas(botoes.map((b) => b.dataset.aba));
  if (!mais.length) return;
  const botaoMais = Object.assign(doc.createElement("button"), { type: "button", id: "aba-mais", textContent: "Mais ▾" });
  botaoMais.setAttribute("aria-expanded", "false");
  botaoMais.setAttribute("aria-controls", "abas-mais");
  const bandeja = Object.assign(doc.createElement("div"), { id: "abas-mais", hidden: true });
  botoes.filter((b) => mais.includes(b.dataset.aba)).forEach((b) => bandeja.append(b));
  nav.append(botaoMais, bandeja);
  const abrir = (sim) => { bandeja.hidden = !sim; botaoMais.setAttribute("aria-expanded", String(sim)); };
  const marcar = () => {
    const ativo = botoes.find((b) => b.getAttribute("aria-current") === "page");
    const escondida = ativo && mais.includes(ativo.dataset.aba);
    if (escondida) botaoMais.setAttribute("aria-current", "page"); else botaoMais.removeAttribute("aria-current");
    botaoMais.textContent = escondida ? ativo.textContent + " ▾" : "Mais ▾";
  };
  botaoMais.addEventListener("click", () => abrir(bandeja.hidden));
  botoes.forEach((b) => b.addEventListener("click", () => { abrir(false); marcar(); }));
  doc.addEventListener("click", (ev) => { if (!bandeja.hidden && !nav.contains(ev.target)) abrir(false); });
  doc.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && !bandeja.hidden) { abrir(false); botaoMais.focus(); } });
  marcar();
}
