// Caixa Vagas (Remotive e repositórios de vagas do GitHub, direto). Pontuada pelo perfil da memória; eu nunca me candidato por você.
import { listarVagas } from "./info.js";
import { criarCaixa, el, idade, linkSeguro } from "./caixa-base.js";

const UMA_HORA = 60 * 60000;  // as APIs públicas têm cota: vagas mudam devagar

function desenhar(d, corpo, ctx) {
  if (d.semPerfil) corpo.append(el("p", { className: "nota", textContent: 'Mostrando as mais recentes. Diga "minha stack é Python e React" na conversa para eu escolher as que combinam com você.' }));
  const lista = el("ul", { className: "caixa-lista" });
  for (const v of d.itens) {
    lista.append(el("li", {}, linkSeguro(v.titulo, v.link),
      el("small", { className: "nota", textContent: ` ${v.fonte}${v.quando ? " · " + idade(v.quando / 1000, ctx.agora?.()) : ""}${v.motivos.length ? " · " + v.motivos.join(", ") : ""}` })));
  }
  corpo.append(lista);
}

export function montar(container, ctx) {
  return criarCaixa(container, ctx, {
    id: "vagas", titulo: "Oportunidades de emprego", ttlMs: UMA_HORA, vazio: "Não achei vagas que combinam com o seu perfil agora.",
    async carregar() {
      const r = await listarVagas(ctx.memoria, ctx.buscar);
      if (!r.itens.length && r.avisos.length >= 2) throw new Error(r.avisos.join("; "));
      return { dados: r, avisos: r.avisos };
    },
    desenhar,
  });
}
