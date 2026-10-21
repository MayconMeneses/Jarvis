// Cartão "Sessões do Claude Code": contagem por estado e até 5 projetos. Nunca mostra conversa. Só leitura.
import { linhas, modulo } from "./pc-cartao.js";
import { textoSessoes } from "./pc-texto.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-sessoes", titulo: "Sessões do Claude Code", rota: "sessoes", desenhar: (corpo, _d, r) => linhas(corpo, textoSessoes(r)) });
