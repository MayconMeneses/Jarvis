// Cartão "E-mails" do PC pareado (sem corpo e sem links; suspeitos só contados).
import { linhas, modulo } from "./pc-cartao.js";
import { textoEmails } from "./motor-pc.js";

export const montar = (container, ctx) => modulo(container, ctx, { id: "pc-emails", titulo: "E-mails", rota: "emails", desenhar: (corpo, _d, r) => linhas(corpo, textoEmails(r)) });
