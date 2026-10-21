// Liga a escuta contínua, a saída de voz (aparelho ou Gemini), o indicador de microfone e o painel Cérebro > Voz ao resto do app.
// A casca/modo foco usa direto `Escuta` (iniciar/parar/estado/aoMudar/entrarFoco/sairFoco) importado de escuta.js.
import { Escuta } from "./escuta.js";
import { montarIndicador } from "./escuta-ui.js";
import { montarPainelVoz } from "./painel-voz.js";
import { comandoDeControle } from "./voz-ativacao.js";
import { criarGemini } from "./voz-gemini.js";
import { saida } from "./voz-saida.js";
import { criarTocador } from "./voz-tocador.js";

// deps: { memoria, nuvem, responder(texto) -> resposta, adicionar(texto, quem), avisar(texto), painel (elemento onde entra o bloco Voz) }
export async function ligarVoz({ memoria, nuvem, responder, adicionar, avisar, painel, doc = globalThis.document }) {
  saida.usarGemini(criarGemini({ chave: () => nuvem.chaveGemini() }), criarTocador());
  saida.aoAviso(avisar);
  saida.aoMudar((e) => Escuta.marcarFala(e === "falando"));

  Escuta.configurar({
    aoIniciar: () => saida.destravar(),
    interromper: () => saida.parar(),
    textoFalado: () => saida.textoAtual,
    aoComando: async (comando) => {
      const controle = comandoDeControle(comando);
      if (controle === "parar-fala") { saida.parar(); return; }
      if (controle === "desligar") { saida.parar(); Escuta.parar(); adicionar("Escuta por voz desligada.", "jarvis aviso"); return; }
      adicionar(comando, "eu");
      await saida.falar(await responder(comando));  // a escuta fala a resposta mesmo com "Falar as respostas" desmarcado: foi um pedido por voz
    },
  });
  montarIndicador(Escuta, { doc });
  doc.addEventListener?.("visibilitychange", () => Escuta.visibilidade(!doc.hidden));
  const painelVoz = await montarPainelVoz(painel, { saida, escuta: Escuta, memoria, nuvem, avisar });

  // O Safari só abre o microfone depois de um toque: se a escuta na conversa estava ligada, religa no primeiro toque na tela.
  if (painelVoz.ligarConversa && Escuta.disponivel()) {
    const religar = () => { doc.removeEventListener("pointerdown", religar); if (!Escuta.ativa) Escuta.iniciar(); };
    doc.addEventListener("pointerdown", religar);
  }
  return Escuta;
}
