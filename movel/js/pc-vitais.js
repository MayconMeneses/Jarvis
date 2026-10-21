// Cartão "Vitais do PC" (CPU, RAM, disco). montar(container, ctx) => { id, titulo, atualizar }.
import { barra, linhas, modulo } from "./pc-cartao.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-vitais", titulo: "Vitais do PC", rota: "vitais", desenhar(corpo, v) {
  barra(corpo, "CPU", v.cpu); barra(corpo, "RAM", v.ram); barra(corpo, "Disco", v.disco);
  linhas(corpo, `RAM: ${v.ram_usada_gb} de ${v.ram_total_gb} GB. Disco: ${v.disco_livre_gb} GB livres de ${v.disco_total_gb} GB.`);
} });
