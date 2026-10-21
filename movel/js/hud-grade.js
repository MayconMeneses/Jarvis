// Grade de caixas do Início: cada caixa vem embrulhada num item com uma barra "subir/descer" que só aparece no modo Reordenar.
// A ordem fica na meta "hud_ordem" (com try/catch: sem armazenamento a ordem vale só nesta sessão). Regras da ordem: hud-ordem.js.
import { CHAVE, PADRAO, anuncio, mover, podeMover, sanear } from "./hud-ordem.js";

const no = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };

export function criarGrade(container, { memoria, anunciar = () => {}, ids = PADRAO }) {
  const itens = new Map();
  let ordem = [...ids], reordenando = false;
  const visiveis = () => ordem.filter((id) => itens.get(id) && !itens.get(id).raiz.hidden);

  async function guardar() { try { await memoria.definirMeta(CHAVE, ordem); } catch { /* sem espaço: a ordem vale só agora */ } }

  function atualizarBotoes() {
    const vis = visiveis();
    for (const id of ordem) {
      const it = itens.get(id);
      if (!it) continue;
      it.sobe.disabled = !podeMover(ordem, id, -1, vis);
      it.desce.disabled = !podeMover(ordem, id, 1, vis);
    }
  }
  function aplicar() { for (const id of ordem) { const it = itens.get(id); if (it) container.append(it.raiz); } atualizarBotoes(); }

  function mexer(id, delta, botao) {
    const vis = visiveis(), nova = mover(ordem, id, delta, vis);
    if (nova.join() === ordem.join()) return;
    ordem = nova;
    aplicar();
    (botao.disabled ? itens.get(id)[delta < 0 ? "desce" : "sobe"] : botao).focus();  // o foco acompanha a caixa que acabou de mexer
    anunciar(anuncio(itens.get(id).titulo, ordem, id, visiveis()));
    guardar();
  }

  function registrar(id, titulo, conteudo, { visivel = true } = {}) {
    if (!ids.includes(id) || itens.has(id)) return null;
    const sobe = no("button", { type: "button", className: "mini", textContent: "▲" }), desce = no("button", { type: "button", className: "mini", textContent: "▼" });
    sobe.setAttribute("aria-label", `Subir ${titulo}`); desce.setAttribute("aria-label", `Descer ${titulo}`);
    const barra = no("div", { className: "mover", hidden: !reordenando }, no("span", { textContent: titulo }), sobe, desce);
    const raiz = no("div", { className: "item-caixa", id: `item-${id}`, hidden: !visivel }, barra, conteudo);
    raiz.dataset.id = id;
    sobe.addEventListener("click", () => mexer(id, -1, sobe));
    desce.addEventListener("click", () => mexer(id, 1, desce));
    itens.set(id, { id, titulo, raiz, barra, sobe, desce });
    container.append(raiz);
    return raiz;
  }

  return {
    registrar,
    get ordem() { return [...ordem]; },
    get reordenando() { return reordenando; },
    async carregar() { try { ordem = sanear(await memoria.meta(CHAVE), ids); } catch { ordem = [...ids]; } aplicar(); },
    definirVisivel(id, sim) { const it = itens.get(id); if (it && it.raiz.hidden === sim) { it.raiz.hidden = !sim; atualizarBotoes(); } },
    reordenar(sim) {
      reordenando = Boolean(sim);
      container.toggleAttribute("data-reordenando", reordenando);
      for (const it of itens.values()) it.barra.hidden = !reordenando;
      atualizarBotoes();
    },
    async restaurar() { ordem = [...ids]; this.reordenar(false); aplicar(); try { await memoria.definirMeta(CHAVE, null); } catch { /* ignorado */ } anunciar("Layout restaurado ao padrão."); },
  };
}
