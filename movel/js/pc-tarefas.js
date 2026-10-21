// Cartão "Tarefas do PC": fila e andamento das tarefas de código. Só leitura.
import { linhas, modulo } from "./pc-cartao.js";
import { textoTarefas } from "./pc-texto.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-tarefas", titulo: "Tarefas do PC", rota: "tarefas", desenhar: (corpo, _d, r) => linhas(corpo, textoTarefas(r)) });
