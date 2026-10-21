// Painel "PC": cartões somente leitura do PC pareado. Cada cartão é um módulo montar(container, ctx); o pacote da casca (HUD) pode
// encaixar qualquer um deles em outro lugar chamando o próprio montar. ctx = { pc }.
import { OFFLINE } from "./pc-pareado.js";
import { el, hora } from "./pc-cartao.js";
import * as vitais from "./pc-vitais.js";
import * as sessoes from "./pc-sessoes.js";
import * as tarefas from "./pc-tarefas.js";
import * as uso from "./pc-uso.js";
import * as radar from "./pc-radar.js";
import * as agenda from "./pc-agenda.js";
import * as emails from "./pc-emails.js";
import * as agentes from "./pc-agentes.js";

export const CARTOES = [vitais, sessoes, tarefas, uso, radar, agenda, emails, agentes];

export function montar(container, ctx) {
  const aviso = el("p", { className: "nota", role: "status", id: "pc-aviso" });
  const botao = el("button", { type: "button", id: "pc-atualizar", textContent: "Atualizar" });
  const lista = el("div", { id: "pc-cartoes" });
  container.append(aviso, el("div", { className: "linha" }, botao), lista);
  const montados = CARTOES.map((m) => m.montar(lista, ctx));

  async function atualizar() {
    if (!(await ctx.pc.pareado())) {
      aviso.textContent = "Pareie com o PC na aba Cérebro (PC pareado) para ver o seu PC aqui.";
      montados.forEach((m) => { m.cartao.corpo.replaceChildren(); m.cartao.rodape.textContent = ""; });
      return [];
    }
    botao.disabled = true;
    aviso.textContent = "Atualizando…";
    try {
      const rs = await Promise.all(montados.map((m) => m.atualizar()));
      const vivas = rs.filter((r) => r.ok && !r.doCache).length, copias = rs.filter((r) => r.ok && r.doCache).length;
      aviso.textContent = vivas ? `Atualizado às ${hora()}.` : copias ? `${OFFLINE} Mostrando as últimas cópias, com a data de cada uma.` : (rs.find((r) => r.erro)?.erro || OFFLINE);
      return rs;
    } finally { botao.disabled = false; }
  }

  botao.addEventListener("click", atualizar);
  container.append(el("p", { className: "nota", textContent: "Somente leitura: vem do seu PC pareado, sem conversas, sem e-mails completos e sem links. Aqui não há botão que execute algo no PC. Com o PC desligado ou fora da rede, mostro a última cópia, com a hora." }));
  return { atualizar, cartoes: montados };
}
