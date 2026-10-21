// Modo FOCO: estado e PONTO DE LIGAÇÃO com a voz (sem DOM, testável no Node). A tela do foco está em foco.js.
//
// CONTRATO para quem cuida da voz (pacote D): importe o singleton e use só isto.
//   import { Foco } from "./foco-estado.js";
//   Foco.definirEstado("ouvindo" | "falando" | "pensando" | "ocioso")   // muda o orbe e o rótulo (EM ESPERA, OUVINDO, PROCESSANDO, FALANDO)
//   Foco.definirFala("texto que a Jarvis está dizendo")                  // linha sob o orbe (texto simples; sem HTML)
//   Foco.definirMicrofone(true | false)                                  // acende/apaga o botão grande (aria-pressed)
//   const desligar = Foco.ligarMicrofone(async ({ ativo }) => { ... });  // chamado quando a pessoa toca no botão grande;
//        // `ativo` = o estado PEDIDO (true = começar a ouvir). Devolva false (ou lance erro) se não conseguiu: o botão volta ao que era.
//   Foco.aoMudar((s) => ...)  // s = { aberto, estado, microfoneAtivo, fala }
//   Foco.abrir() / Foco.fechar() / Foco.alternar()
// Sem nenhum ouvinte registrado, o botão grande usa o "Conversar por voz" que já existe na conversa (ver foco.js).
export const ESTADOS = ["ocioso", "ouvindo", "pensando", "falando"];

export function criarEstadoFoco() {
  const s = { aberto: false, estado: "ocioso", microfoneAtivo: false, fala: "" };
  const ouvintes = new Set(), microfones = new Set(), pedidos = new Set();
  const avisar = () => ouvintes.forEach((f) => { try { f({ ...s }); } catch { /* tela */ } });
  const foco = {
    get aberto() { return s.aberto; },
    get estado() { return s.estado; },
    get microfoneAtivo() { return s.microfoneAtivo; },
    get fala() { return s.fala; },
    abrir() { if (!s.aberto) { s.aberto = true; avisar(); } },
    fechar() { if (s.aberto) { s.aberto = false; avisar(); } },
    alternar() { if (s.aberto) foco.fechar(); else foco.abrir(); },
    definirEstado(estado) { if (ESTADOS.includes(estado) && estado !== s.estado) { s.estado = estado; avisar(); } },
    definirFala(texto) { const t = String(texto ?? "").slice(0, 400); if (t !== s.fala) { s.fala = t; avisar(); } },
    definirMicrofone(ativo) { const a = Boolean(ativo); if (a !== s.microfoneAtivo) { s.microfoneAtivo = a; avisar(); } },
    aoMudar(fn) { ouvintes.add(fn); return () => ouvintes.delete(fn); },
    ligarMicrofone(fn) { microfones.add(fn); return () => microfones.delete(fn); },
    // Para o foco.js: sem nenhum ouvinte de microfone, quem desenha cai no recurso que já existe.
    aoFaltarMicrofone(fn) { pedidos.add(fn); return () => pedidos.delete(fn); },
    temMicrofone: () => microfones.size > 0,
    // Toque no botão grande. Devolve o estado final do microfone.
    async pressionarMicrofone() {
      const pedido = !s.microfoneAtivo;
      if (!microfones.size) { for (const f of pedidos) { try { f({ ativo: pedido }); } catch { /* tela */ } } return s.microfoneAtivo; }
      let ok = true;
      for (const f of microfones) {
        try { if ((await f({ ativo: pedido })) === false) ok = false; } catch { ok = false; }
      }
      if (ok) foco.definirMicrofone(pedido);
      return s.microfoneAtivo;
    },
  };
  return foco;
}

export const Foco = criarEstadoFoco();
