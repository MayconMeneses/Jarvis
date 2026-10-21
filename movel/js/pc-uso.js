// Cartão "Uso e cota do Claude": estimativa (o Claude não expõe a cota). Custo é equivalente em API, rotulado como estimado.
import { barra, linhas, modulo } from "./pc-cartao.js";
import { textoUso } from "./pc-texto.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-uso", titulo: "Uso e cota do Claude", rota: "uso", desenhar(corpo, u, r) {
  if (u.cota.janela_5h.pct !== null) barra(corpo, "Janela de 5 h (estimada)", Math.min(100, Math.round(u.cota.janela_5h.pct)));
  if (u.cota.semana.pct !== null) barra(corpo, "Semana (estimada)", Math.min(100, Math.round(u.cota.semana.pct)));
  linhas(corpo, textoUso(r));
} });
