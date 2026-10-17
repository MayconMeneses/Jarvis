// O leque de modelos de um provedor: TODOS os de conversa, na ordem em que vale tentar, lembrando quais já foram encerrados.
// Mesma lógica do PC (jarvis/brains/modelos.py): a NVIDIA, por exemplo, aposenta modelos de tempos em tempos.
import { fold } from "./util.js";

export const PREFERIDOS_NVIDIA = ["nvidia/llama-3.1-nemotron-70b-instruct", "mistralai/mistral-large-2-instruct", "nvidia/llama-3.1-nemotron-51b-instruct",
  "nvidia/nemotron-3-super-120b-a12b", "google/gemma-3-12b-it", "nv-mistralai/mistral-nemo-12b-instruct", "mistralai/mistral-7b-instruct-v0.3",
  "deepseek-ai/deepseek-v4.1-flash", "z-ai/glm-5.3-flash", "moonshotai/kimi-k2.6"];
// Nunca são de conversa de texto.
export const NAO_E_CONVERSA = ["embed", "guard", "safety", "reward", "parse", "vlm", "vision", "vila", "neva", "nvclip", "riva", "deplot", "fuyu", "kosmos", "retriev",
  "calibration", "detector", "cosmos", "topic-control", "diffusion", "tts", "audio", "image", "rerank", "translate", "-base", "whisper", "moderation", "dall-e", "transcribe", "realtime"];
// Servem, mas ficam para o fim (raciocinam em voz alta, são de código ou experimentais).
export const ULTIMO_RECURSO = ["reasoning", "coder", "codegemma", "codellama", "starcoder", "preview", "exp", "thinking", "lite", "live", "omni"];
export const VALIDADE_MORTO = 3 * 86400000;  // um modelo "encerrado" é revisto depois de 3 dias
export const MAX_TENTATIVAS = 15;

const tem = (m, lista) => lista.some((p) => m.toLowerCase().includes(p));
const versao = (m) => parseFloat((m.match(/\d+(\.\d+)?/) || [0])[0]);

export function ordenar(provedor, modelos) {
  const uteis = [...new Set(modelos)].filter((m) => !tem(m, NAO_E_CONVERSA));
  if (provedor === "gemini") {  // os "flash" mais novos primeiro (rápidos e baratos), depois o resto
    const flash = uteis.filter((m) => /gemini/.test(m) && /flash/.test(m) && !tem(m, ULTIMO_RECURSO)).sort((a, b) => versao(b) - versao(a));
    return [...flash, ...uteis.filter((m) => !flash.includes(m) && !tem(m, ULTIMO_RECURSO)), ...uteis.filter((m) => tem(m, ULTIMO_RECURSO))];
  }
  const preferidos = provedor === "nvidia" ? PREFERIDOS_NVIDIA.filter((m) => uteis.includes(m)) : [];
  const resto = uteis.filter((m) => !preferidos.includes(m));
  const normais = resto.filter((m) => !tem(m, ULTIMO_RECURSO)).sort((a, b) => (tem(a, ["instruct", "chat", "-it", "versatile", "gpt", "llama"]) ? 0 : 1) - (tem(b, ["instruct", "chat", "-it", "versatile", "gpt", "llama"]) ? 0 : 1) || (a < b ? -1 : 1));
  return [...preferidos, ...normais, ...resto.filter((m) => tem(m, ULTIMO_RECURSO)).sort()];
}

export class EstadoLeque {
  constructor(armazem, agora = () => Date.now()) { this.armazem = armazem; this.agora = agora; }
  _chave(p) { return "leque:" + p; }
  async _ler(p) { return (await this.armazem.ler(this._chave(p))) || { pool: [], bom: null, mortos: {} }; }
  async pool(p) { return (await this._ler(p)).pool; }
  async definirPool(p, pool) { const e = await this._ler(p); e.pool = pool; await this.armazem.gravar(this._chave(p), e); }
  async bom(p) { return (await this._ler(p)).bom; }
  async marcarBom(p, m) { const e = await this._ler(p); if (e.bom !== m) { e.bom = m; await this.armazem.gravar(this._chave(p), e); } }
  async mortos(p) { const e = await this._ler(p), agora = this.agora(); return new Set(Object.entries(e.mortos).filter(([, t]) => agora - t < VALIDADE_MORTO).map(([m]) => m)); }
  async marcarMorto(p, m) { const e = await this._ler(p); e.mortos[m] = this.agora(); await this.armazem.gravar(this._chave(p), e); }
  // O último que funcionou, o configurado e o resto do leque, sem os encerrados e sem repetir.
  async ordem(p, padrao) {
    const mortos = await this.mortos(p), e = await this._ler(p), vistos = [];
    for (const m of [e.bom, padrao, ...e.pool]) if (m && !vistos.includes(m) && !mortos.has(m)) vistos.push(m);
    return vistos;
  }
}

export const semAcento = fold;
