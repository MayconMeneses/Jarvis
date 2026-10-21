// Liga o modo foco à escuta contínua (escuta.js, pacote D): entrar/sair do foco, botão de microfone grande e estado do orbe.
// Tudo síncrono dentro do toque da pessoa (o iOS só libera o microfone dentro de um gesto). Sem Escuta disponível, o botão cai no "Conversar por voz".
import { Escuta } from "./escuta.js";
import { Foco } from "./foco-estado.js";

// Estado da escuta -> estado do orbe.
export const ESTADO_DO_ORBE = { desligado: "ocioso", aguardando: "ocioso", ouvindo: "ouvindo", processando: "pensando", falando: "falando" };

export function ligarFocoVoz({ foco = Foco, escuta = Escuta } = {}) {
  let aberto = false;
  foco.aoMudar((s) => {
    if (s.aberto === aberto) return;
    aberto = s.aberto;
    try { if (aberto) escuta.entrarFoco(); else escuta.sairFoco(); } catch { /* sem escuta: o foco segue só com o botão */ }
  });
  foco.ligarMicrofone(({ ativo }) => {
    if (!ativo) { escuta.parar(); return true; }
    return escuta.iniciar() !== false;  // false = sem suporte ou sem permissão: o botão não acende
  });
  escuta.aoMudar((estado) => {
    foco.definirMicrofone(estado !== "desligado");
    if (ESTADO_DO_ORBE[estado] && (aberto || estado !== "desligado")) foco.definirEstado(ESTADO_DO_ORBE[estado]);
  });
  return foco;
}
