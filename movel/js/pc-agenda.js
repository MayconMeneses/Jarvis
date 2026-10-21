// Cartão "Agenda" do PC pareado.
import { linhas, modulo } from "./pc-cartao.js";
import { textoAgenda } from "./motor-pc.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-agenda", titulo: "Agenda", rota: "agenda", desenhar: (corpo, _d, r) => linhas(corpo, textoAgenda(r)) });
