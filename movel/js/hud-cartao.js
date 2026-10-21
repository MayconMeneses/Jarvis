// Cartão central do HUD (sobre o orbe): saudação e três abas, AGENDA / E-MAILS / NOTÍCIAS. Só textContent: o que vem do PC e da internet é texto de terceiros.
// Os resumos vêm de hud-briefing.js (puro). Tocar no título abre onde está a lista completa.
import { ABAS, proximaAba, resumoAgenda, resumoEmails, resumoNoticias, saudacao } from "./hud-briefing.js";

const no = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };

export function montarCartao(raiz, { aoAbrir = () => {} } = {}) {
  const dados = { agenda: null, lembretes: [], emails: null, noticias: [], nome: "", hora: new Date().getHours() };
  let aba = "agenda";
  const ola = no("p", { className: "bf-ola" }), lista = no("div", { className: "bf-abas" });
  lista.setAttribute("role", "tablist"); lista.setAttribute("aria-label", "Resumo do dia");
  const painel = no("div", { className: "bf-painel", id: "bf-painel" });
  painel.setAttribute("role", "tabpanel");
  const botoes = new Map();
  for (const a of ABAS) {
    const b = no("button", { type: "button", className: "bf-aba", textContent: a.rotulo, id: `bf-aba-${a.id}` });
    b.setAttribute("role", "tab"); b.setAttribute("aria-controls", "bf-painel");
    b.addEventListener("click", () => escolher(a.id));
    b.addEventListener("keydown", (ev) => { const p = proximaAba(aba, ev.key); if (p) { ev.preventDefault(); escolher(p); botoes.get(p).focus(); } });
    botoes.set(a.id, b);
    lista.append(b);
  }
  raiz.replaceChildren(ola, lista, painel);

  const resumo = () => (aba === "agenda" ? resumoAgenda(dados.agenda, dados.lembretes) : aba === "emails" ? resumoEmails(dados.emails) : resumoNoticias(dados.noticias));
  function desenhar() {
    ola.textContent = saudacao(dados.hora, dados.nome).toUpperCase();
    for (const [id, b] of botoes) { b.setAttribute("aria-selected", String(id === aba)); b.tabIndex = id === aba ? 0 : -1; }
    painel.setAttribute("aria-labelledby", `bf-aba-${aba}`);
    const r = resumo(), titulo = no("button", { type: "button", className: "bf-titulo", textContent: r.titulo });
    titulo.setAttribute("aria-label", `${r.titulo}. Abrir a lista completa`);
    titulo.addEventListener("click", () => aoAbrir(aba));
    painel.replaceChildren(titulo, ...r.linhas.map((l) => no("p", { className: "bf-linha", textContent: l })));
  }
  function escolher(id) { aba = id; desenhar(); }
  desenhar();
  return { definir(parcial) { Object.assign(dados, parcial); desenhar(); }, escolher, get aba() { return aba; } };
}
