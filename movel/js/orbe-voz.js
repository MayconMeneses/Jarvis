// Liga o orbe à fala e à escuta do navegador. HONESTO: o SpeechSynthesis não expõe o áudio, então a fala é animada
// "pelo ritmo, não pelo som real": um envelope sintético por sílabas e pontuação (ajustado pelo rate) + um pulso a cada
// limite de palavra (onboundary), que também reajusta o relógio. A escuta usa onstart/onspeechstart/onresult do
// reconhecimento. O microfone real (AnalyserNode) é uma OPÇÃO DESLIGADA: no iPhone, getUserMedia junto com o
// reconhecimento de fala pode derrubar um dos dois ou trocar a rota de áudio (ainda não testado em aparelho real).

const SILABA_MS = 190;  // ~5 sílabas por segundo em português falado em rate 1
const PAUSAS = { ",": 180, ";": 220, ":": 220, ".": 380, "!": 380, "?": 380, "…": 380 };

export const contarSilabas = (palavra) => {
  const grupos = palavra.match(/[aeiouáéíóúâêôãõàü]+/gi);
  if (grupos) return grupos.length;
  return palavra.replace(/\W/g, "").length ? Math.max(1, Math.ceil(palavra.length / 3)) : 0;  // números e siglas
};

const ruido = (n) => { const x = Math.sin(n * 12.9898) * 43758.5453; return x - Math.floor(x); };

// Plano de tempo do texto: onde cada palavra cai (em ms) e qual a amplitude em cada instante.
export function criarPlano(texto, rate = 1) {
  const r = Math.max(0.5, Math.min(2, Number(rate) || 1));
  const palavras = [];
  let t = 0;
  for (const m of String(texto).matchAll(/[^\s]+/g)) {
    const bruta = m[0], miolo = bruta.replace(/[.,;:!?…"'()]+$/g, ""), final = bruta.slice(miolo.length).slice(-1);
    const sil = contarSilabas(miolo), dur = (sil * SILABA_MS) / r, pausa = (PAUSAS[final] || 0) / r;
    palavras.push({ ini: m.index, t0: t, t1: t + dur, sil, pausa });
    t += dur + pausa;
  }
  const total = t;
  const nivelEm = (ms) => {
    if (ms < 0 || ms >= total) return 0;
    const p = palavras.find((w) => ms < w.t1 + w.pausa);
    if (!p || ms >= p.t1 || !p.sil) return 0.04;  // pausa: o orbe quase se aquieta
    const fase = ((ms - p.t0) / (p.t1 - p.t0)) * p.sil, k = Math.floor(fase);
    const pico = 0.55 + 0.4 * ruido(p.ini + k);  // cada sílaba tem uma altura um pouco diferente
    return 0.12 + (pico - 0.12) * Math.sin(Math.PI * (fase - k)) ** 2;
  };
  const tempoDoChar = (indice) => {
    const p = palavras.findLast ? palavras.findLast((w) => w.ini <= indice) : [...palavras].reverse().find((w) => w.ini <= indice);
    return p ? p.t0 : 0;
  };
  return { total, palavras, nivelEm, tempoDoChar };
}

// Devolve os manipuladores para um SpeechSynthesisUtterance; "texto" deve ser o MESMO que será falado (charIndex confere).
export function ligarFala(orbe, texto, rate = 1, agora = () => performance.now()) {
  const plano = criarPlano(texto, rate);
  let t0 = 0;
  return {
    plano,
    inicio() { t0 = agora(); orbe.fonte = (ts) => plano.nivelEm((ts || agora()) - t0); orbe.definirEstado("falando"); },
    limite(ev) {  // limite de palavra: pulso real e relógio reajustado ao ponto que o navegador diz estar falando
      if (ev && ev.name && ev.name !== "word") return;
      orbe.pulso(0.85);
      if (ev && Number.isFinite(ev.charIndex)) t0 = agora() - plano.tempoDoChar(ev.charIndex);
    },
    fim() { orbe.fonte = null; if (orbe.estadoAtual === "falando") orbe.definirEstado("ocioso"); },
  };
}

// Microfone real (opcional e desligado por padrão): nível 0..1 a partir de um AnalyserNode.
export async function analisadorMicrofone(api = { getUserMedia: (c) => navigator.mediaDevices.getUserMedia(c), Contexto: globalThis.AudioContext || globalThis.webkitAudioContext }) {
  const fluxo = await api.getUserMedia({ audio: true });
  const ctx = new api.Contexto();
  const analisador = ctx.createAnalyser();
  analisador.fftSize = 256;
  analisador.smoothingTimeConstant = 0.6;
  ctx.createMediaStreamSource(fluxo).connect(analisador);
  const dados = new Uint8Array(analisador.fftSize);
  return {
    nivel() { analisador.getByteTimeDomainData(dados); let s = 0; for (const v of dados) s += ((v - 128) / 128) ** 2; return Math.min(1, Math.sqrt(s / dados.length) * 4); },
    parar() { fluxo.getTracks().forEach((x) => x.stop()); ctx.close(); },
  };
}

// Reconhecimento de fala: estado "ouvindo" e pulsos nos eventos. micReal=true usa o analisador acima (padrão: desligado).
export function ligarEscuta(orbe, rec, { micReal = false, criarAnalisador = analisadorMicrofone } = {}) {
  let mic = null;
  rec.addEventListener("start", async () => {
    orbe.definirEstado("ouvindo");
    if (micReal) { try { mic = await criarAnalisador(); orbe.fonte = () => mic.nivel(); } catch { mic = null; } }
  });
  rec.addEventListener("speechstart", () => orbe.pulso(0.9));
  rec.addEventListener("result", () => orbe.pulso(0.7));
  rec.addEventListener("end", () => {
    if (mic) { mic.parar(); mic = null; }
    orbe.fonte = null;
    if (orbe.estadoAtual === "ouvindo") orbe.definirEstado("ocioso");
  });
}
