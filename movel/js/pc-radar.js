// Cartão "Radar do PC": títulos do último boletim, com fonte e hora. Sem corpo e sem links.
import { linhas, modulo } from "./pc-cartao.js";
import { textoRadar } from "./pc-texto.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-radar", titulo: "Radar do PC", rota: "radar", desenhar: (corpo, _d, r) => linhas(corpo, textoRadar(r)) });
