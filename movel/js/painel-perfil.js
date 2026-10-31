// Cérebro > Meu perfil: ver e editar o que a Jarvis sabe sobre você. Mudar ou apagar abre um cartão "Aprovar/Cancelar"; nada grava sem o Aprovar.
// Tudo com textContent (o texto vem do usuário e das notas, nunca vira HTML).
import { CAMPOS, MAX_VALOR, aprovar, compilar, proposta } from "./perfil-usuario.js";

const $ = (id) => document.getElementById(id);
const el = (tag, texto, classe) => { const e = document.createElement(tag); if (texto) e.textContent = texto; if (classe) e.className = classe; return e; };
const ORIGEM = { definido: "definido por você", deduzido: "deduzido das suas notas" };

// Cartão de aprovação dentro do campo. `feito()` recarrega a lista depois.
export function cartaoPerfil({ memoria, prop, onde, feito, avisar }) {
  const c = el("div", "", "cartao-memoria"), linha = el("div", "", "linha");
  c.setAttribute("role", "group");
  c.setAttribute("aria-label", "Aprovar mudança no perfil");
  const aprovarBtn = el("button", "Aprovar"), cancelar = el("button", "Cancelar");
  aprovarBtn.type = cancelar.type = "button";
  cancelar.addEventListener("click", () => c.remove());
  aprovarBtn.addEventListener("click", async () => {
    aprovarBtn.disabled = cancelar.disabled = true;
    try { avisar(await aprovar(memoria, prop.campo, prop.valor)); await feito(); } catch (e) { avisar(`Não consegui guardar (${e.message}).`); c.remove(); }
  });
  linha.append(aprovarBtn, cancelar);
  c.append(el("pre", prop.texto), linha);
  onde.querySelector?.(".cartao-memoria")?.remove();
  onde.append(c);
  return c;
}

function campo({ id, nome, dado, memoria, feito, avisar }) {
  const sec = el("section", "", "pf-campo");
  const rotulo = el("label", nome), origem = el("small", dado ? `(${ORIGEM[dado.origem]})` : "(ainda vazio)");
  rotulo.htmlFor = `pf-${id}`;
  const area = el("textarea");
  Object.assign(area, { id: `pf-${id}`, rows: 2, maxLength: MAX_VALOR, value: dado ? dado.valor : "" });
  const salvar = el("button", "Pedir para salvar"), apagar = el("button", "Pedir para apagar", "danger");
  salvar.type = apagar.type = "button";
  apagar.disabled = !dado || dado.origem !== "definido";  // o deduzido vem das notas: edita-se em Memória
  if (apagar.disabled) apagar.title = "Só dá para apagar o que você definiu. O resto vem das suas notas (Memória).";
  const linha = el("div", "", "linha");
  linha.append(salvar, apagar);
  sec.append(rotulo, origem, area, linha);
  const pedir = (valor) => async () => {
    try { cartaoPerfil({ memoria, prop: await proposta(memoria, id, valor()), onde: sec, feito, avisar }); } catch (e) { avisar(`Não deu: ${e.message}.`); }
  };
  salvar.addEventListener("click", pedir(() => area.value));
  apagar.addEventListener("click", pedir(() => ""));
  return sec;
}

export function ligarPerfil({ memoria, avisar }) {
  async function carregar() {
    const lista = $("pf-lista");
    lista.setAttribute("aria-busy", "true");
    try {
      const p = await compilar(memoria);
      lista.replaceChildren(...Object.entries(CAMPOS).map(([id, nome]) => campo({ id, nome, dado: p[id], memoria, feito: carregar, avisar })));
    } catch (e) { avisar(`Não consegui ler o perfil (${e.message}).`); }
    lista.setAttribute("aria-busy", "false");
  }
  $("painel-perfil").addEventListener("toggle", () => { if ($("painel-perfil").open) carregar(); });
  return carregar;
}
