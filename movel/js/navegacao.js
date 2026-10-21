// Navegação do celular: barra rápida embaixo (Início, Conversa, Foco, Menu) e o menu ☰ agrupado, que abre de baixo (alcance do polegar)
// com TODAS as abas e painéis. A barra de abas antiga (#abas) continua no DOM, escondida, como fonte da verdade: cada item do menu
// "toca" no botão dela, então o resto do app (retomada da aba, abertura de painéis) segue igual.
import { itemAtual, montarMenu, proximoItem } from "./menu-grupos.js";

export const PRINCIPAIS = 4;  // (legado) quantas abas cabiam na barra antiga
export function dividirAbas(ids, max = PRINCIPAIS) {
  return ids.length <= max + 1 ? { barra: [...ids], mais: [] } : { barra: ids.slice(0, max), mais: ids.slice(max) };
}

const no = (doc, tag, props = {}, ...filhos) => { const n = Object.assign(doc.createElement(tag), props); n.append(...filhos); return n; };

function botaoRapido(doc, id, rotulo, icone, classe = "rapido") {
  const b = no(doc, "button", { type: "button", id, className: classe });
  const i = no(doc, "span", { className: "rapido-icone", textContent: icone });
  i.setAttribute("aria-hidden", "true");
  b.append(i, no(doc, "span", { textContent: rotulo }));
  return b;
}

export function ligarNavegacao({ nav = document.getElementById("abas"), doc = document, aoFoco = () => {}, aoRestaurar = () => {} } = {}) {
  const abas = [...nav.querySelectorAll("button[data-aba]")];
  const grupos = montarMenu(abas.map((b) => ({ id: b.dataset.aba, rotulo: b.textContent })));
  const botaoAba = (id) => abas.find((b) => b.dataset.aba === id);
  const atual = () => abas.find((b) => b.getAttribute("aria-current") === "page")?.dataset.aba;

  // ── Barra rápida ──
  const bInicio = botaoRapido(doc, "rapido-inicio", "Início", "◎"), bConversa = botaoRapido(doc, "rapido-conversa", "Conversa", "✎");
  const bFoco = botaoRapido(doc, "rapido-foco", "Foco", "●", "rapido rapido-foco"), bMenu = botaoRapido(doc, "rapido-menu", "Menu", "☰");
  bFoco.setAttribute("aria-label", "Modo foco: orbe em tela cheia e microfone");
  bMenu.setAttribute("aria-haspopup", "dialog"); bMenu.setAttribute("aria-expanded", "false"); bMenu.setAttribute("aria-controls", "menu");
  const barra = no(doc, "nav", { id: "barra-rapida" }, bInicio, bConversa, bFoco, bMenu);
  barra.setAttribute("aria-label", "Acesso rápido");

  // ── Menu ──
  const lista = [];  // botões na ordem, para as setas
  const folha = no(doc, "div", { id: "menu", hidden: true }), fundo = no(doc, "div", { id: "menu-fundo", hidden: true });
  folha.setAttribute("role", "dialog"); folha.setAttribute("aria-modal", "true"); folha.setAttribute("aria-label", "Menu");
  const painel = no(doc, "div", { className: "menu-painel" }), fechar = no(doc, "button", { type: "button", className: "menu-fechar", textContent: "Fechar" });
  painel.append(no(doc, "div", { className: "menu-topo" }, no(doc, "h2", { textContent: "Menu" }), fechar));
  for (const g of grupos) {
    const titulo = no(doc, "h3", { className: "menu-grupo", textContent: g.rotulo, id: `menu-g-${g.id}` }), ul = no(doc, "ul", { className: "menu-lista" });
    ul.setAttribute("aria-labelledby", titulo.id);
    for (const i of g.itens) {
      const b = no(doc, "button", { type: "button", className: "menu-item", textContent: i.rotulo });
      b.dataset.item = i.id;
      b.addEventListener("click", () => ir(i));
      lista.push(b);
      ul.append(no(doc, "li", {}, b));
    }
    painel.append(titulo, ul);
  }
  const restaurar = no(doc, "button", { type: "button", className: "menu-item menu-restaurar", textContent: "Restaurar layout" });
  restaurar.addEventListener("click", () => { aoRestaurar(); abrir(false); });
  lista.push(restaurar);
  painel.append(no(doc, "p", { className: "nota", textContent: "Restaurar layout volta a ordem das caixas do Início ao padrão." }), restaurar);
  folha.append(painel);
  doc.getElementById("app").append(barra);
  doc.body.append(fundo, folha);

  let voltarPara = null;
  function abrir(sim) {
    folha.hidden = fundo.hidden = !sim;
    bMenu.setAttribute("aria-expanded", String(sim));
    doc.documentElement.toggleAttribute("data-menu", sim);
    if (sim) { voltarPara = doc.activeElement; (lista.find((b) => b.dataset.item === itemAtual(grupos, atual())) || lista[0]).focus(); }
    else { voltarPara?.focus?.(); voltarPara = null; }
  }
  function ir(i) {
    abrir(false);
    if (i.acao === "foco") { aoFoco(); return; }
    botaoAba(i.aba)?.click();
    if (i.clicar) doc.getElementById(i.clicar)?.click();
    if (i.abrir) { const d = doc.getElementById(i.abrir); if (d) d.open = true; d?.scrollIntoView?.({ block: "start" }); }
    if (i.rolarPara) doc.getElementById(i.rolarPara)?.scrollIntoView?.({ block: "start" });
  }
  bInicio.addEventListener("click", () => botaoAba("hud")?.click());
  bConversa.addEventListener("click", () => botaoAba("conversa")?.click());
  bFoco.addEventListener("click", () => aoFoco());
  bMenu.addEventListener("click", () => abrir(folha.hidden));
  fechar.addEventListener("click", () => abrir(false));
  fundo.addEventListener("click", () => abrir(false));
  doc.addEventListener("keydown", (ev) => {
    if (folha.hidden) return;
    if (ev.key === "Escape") { abrir(false); return; }
    const prox = proximoItem(lista.indexOf(doc.activeElement), lista.length, ev.key);
    if (prox !== null) { ev.preventDefault(); lista[prox].focus(); return; }
    if (ev.key === "Tab") {  // o foco não escapa da folha enquanto ela está aberta
      const todos = [fechar, ...lista], n = todos.length;
      ev.preventDefault();
      todos[(todos.indexOf(doc.activeElement) + (ev.shiftKey ? -1 : 1) + n) % n].focus();
    }
  });

  // A barra e o menu acompanham a aba atual (quem muda é o main.js, no clique do botão escondido).
  const marcarRapido = (b, sim) => { if (sim) b.setAttribute("aria-current", "page"); else b.removeAttribute("aria-current"); };
  const marcar = () => {
    const a = atual(), item = itemAtual(grupos, a);
    marcarRapido(bInicio, a === "hud"); marcarRapido(bConversa, a === "conversa");
    for (const b of lista) marcarRapido(b, Boolean(b.dataset.item) && b.dataset.item === item);
  };
  if (window.MutationObserver) new MutationObserver(marcar).observe(nav, { attributes: true, attributeFilter: ["aria-current"], subtree: true });
  marcar();
  return { abrir, ir, grupos };
}
