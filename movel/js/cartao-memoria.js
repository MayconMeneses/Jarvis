// Cartão "Guardar esta lembrança?" na conversa. Só textContent, porque o texto veio do modelo.
import { diferenca, guardarAprovada, refDaProposta } from "./memoria-viva.js";

const el = (tag, texto, classe) => { const e = document.createElement(tag); if (texto) e.textContent = texto; if (classe) e.className = classe; return e; };

// Mostra o cartão no fim da lista de mensagens. Devolve o elemento (os testes e a tela usam).
export async function mostrarCartao({ proposta, memoria, dadosExternos = false, onde, aoTerminar = () => {} }) {
  const ref = refDaProposta(proposta), existente = await memoria.ler(ref), dif = diferenca(existente, proposta);
  const cartao = el("div", "", "msg aviso cartao-memoria");
  cartao.setAttribute("role", "group");
  cartao.setAttribute("aria-label", "Guardar esta lembrança?");
  cartao.append(el("b", "Guardar esta lembrança?"), el("div", `Nota: ${ref}`, "nota"));
  if (dif) {
    cartao.append(el("div", "Já existe uma nota com esse título. Ao guardar, ela será substituída:", "nota"),
      el("pre", `Antes:\n${dif.antes}`), el("pre", `Depois:\n${dif.depois}`));
  } else if (existente) {
    cartao.append(el("div", "Já existe uma nota igual: nada muda.", "nota"));
  } else cartao.append(el("pre", proposta.texto));
  if (dadosExternos) cartao.append(el("div", "Atenção: nesta resposta entraram dados de site, notícia ou pesquisa (não verificados). Confira antes de guardar.", "nota aviso"));
  const linha = el("div", "", "linha"), guardar = el("button", "Guardar"), descartar = el("button", "Descartar");
  guardar.type = descartar.type = "button";
  const fechar = (texto) => { cartao.replaceChildren(el("small", texto)); aoTerminar(texto); };
  guardar.addEventListener("click", async () => {
    guardar.disabled = descartar.disabled = true;
    try { await guardarAprovada(memoria, proposta, dadosExternos); fechar(`Guardado em "${ref}".`); } catch (e) { fechar(`Não consegui guardar (${e.message}).`); }
  });
  descartar.addEventListener("click", () => fechar("Descartado. Nada foi guardado."));
  linha.append(guardar, descartar);
  cartao.append(linha);
  onde.appendChild(cartao);
  onde.scrollTop = onde.scrollHeight;
  return cartao;
}
