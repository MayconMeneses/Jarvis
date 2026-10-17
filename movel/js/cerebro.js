// Cérebro de IA DENTRO do celular (WebLLM + WebGPU): o modelo baixa uma vez para o aparelho e roda sem servidor.
// A biblioteca só é carregada quando o usuário liga o cérebro (código de terceiros, versão fixa, licença Apache-2.0).
export const VERSAO_WEBLLM = "0.2.86";
export const URL_WEBLLM = `https://cdn.jsdelivr.net/npm/@mlc-ai/web-llm@${VERSAO_WEBLLM}/+esm`;

// Do menor ao maior. Os tamanhos são aproximados; o iPhone 13 Pro Max (6 GB) aguenta até ~1B com folga.
export const MODELOS = [
  { id: "SmolLM2-360M-Instruct-q4f16_1-MLC", rotulo: "Mínimo (360M)", mb: 380, nota: "Rápido e simples; erra mais." },
  { id: "Qwen2.5-0.5B-Instruct-q4f16_1-MLC", rotulo: "Leve (0,5B)", mb: 950, nota: "Bom equilíbrio para aparelhos de 4 a 6 GB." },
  { id: "Llama-3.2-1B-Instruct-q4f16_1-MLC", rotulo: "Recomendado (Llama 1B)", mb: 880, nota: "Entende português e é o mais testado: recomendado para iPhone." },
  { id: "gemma3-1b-it-q4f16_1-MLC", rotulo: "Gemma 3 (1B)", mb: 710, nota: "Bom em português, mas em alguns aparelhos o WebLLM recusa a configuração dele; se der erro, use o Llama." },
  { id: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC", rotulo: "Mais capaz (1,5B)", mb: 1630, nota: "Só em aparelhos com 8 GB ou mais." },
];
// Llama 3.2 1B é o recomendado: entende português e não usa janela deslizante (o Gemma 3 deu conflito de configuração num iPhone real).
export const RECOMENDADO = "Llama-3.2-1B-Instruct-q4f16_1-MLC";

// Alguns modelos (Gemma 3) vêm com janela de contexto E janela deslizante positivas e o WebLLM recusa com o erro
// "Only one of context_window_size and sliding_window_size can be positive". Tenta como está e, se o erro for esse,
// com cada uma das janelas desligada (-1), uma de cada vez.
export const AJUSTES_DE_JANELA = [undefined, { sliding_window_size: -1 }, { context_window_size: -1 }];
const erroDeJanela = (e) => /sliding_window_size|context_window_size/.test(String(e?.message || e));

export class Cerebro {
  constructor({ importar = (url) => import(url), gpu = () => globalThis.navigator?.gpu } = {}) {
    this.importar = importar; this.gpu = gpu; this.lib = null; this.engine = null; this.modelo = null;
  }

  suportado() { return Boolean(this.gpu()); }
  ligado() { return this.engine !== null; }

  async _biblioteca() { this.lib ||= await this.importar(URL_WEBLLM); return this.lib; }

  // Só oferece os modelos que a versão da biblioteca realmente tem.
  async modelosDisponiveis() {
    const lib = await this._biblioteca();
    const existentes = new Set((lib.prebuiltAppConfig?.model_list || []).map((m) => m.model_id));
    return MODELOS.filter((m) => existentes.has(m.id));
  }

  async carregar(id, aoProgredir = () => {}) {
    if (!this.suportado()) throw new Error("Este navegador não tem WebGPU. No iPhone é preciso o iOS 26 ou mais novo (Safari).");
    if (!MODELOS.some((m) => m.id === id)) throw new Error("modelo desconhecido");
    const lib = await this._biblioteca();
    await this.descarregar();
    const config = { initProgressCallback: (p) => aoProgredir(p.text || "", p.progress ?? 0) };
    let ultimoErro;
    for (const ajuste of AJUSTES_DE_JANELA) {
      try {
        this.engine = await lib.CreateMLCEngine(id, config, ajuste);
        this.modelo = id;
        return;
      } catch (e) {
        ultimoErro = e;
        if (!erroDeJanela(e)) throw e;  // outro problema (memória, rede): não adianta mexer nas janelas
      }
    }
    throw new Error(`${ultimoErro.message} — este modelo não funcionou neste aparelho; escolha outro na lista (o Llama 1B é o mais seguro).`);
  }

  async _gerar(mensagens, aoReceber) {
    let texto = "";
    const fluxo = await this.engine.chat.completions.create({ messages: mensagens, stream: true, max_tokens: 600, temperature: 0.4 });
    for await (const pedaco of fluxo) {
      texto += pedaco.choices?.[0]?.delta?.content || "";
      aoReceber(texto);
    }
    return texto.trim();
  }

  // Se o contexto estourar, tenta de novo só com o sistema e a última fala; se o aparelho perder a GPU, religa o modelo e tenta de novo.
  async perguntar(mensagens, aoReceber = () => {}, aoReligar = () => {}) {
    if (!this.engine) throw new Error("o cérebro de IA não está ligado");
    try {
      return await this._gerar(mensagens, aoReceber);
    } catch (e) {
      const msg = String(e?.message || e);
      if (/context|exceed|too long|prompt tokens|window/i.test(msg) && mensagens.length > 2) {
        return this._gerar([mensagens[0], mensagens[mensagens.length - 1]], aoReceber);
      }
      if (/device|lost|gpu|webgpu|abort|dispose/i.test(msg) && this.modelo) {
        aoReligar("O iPhone liberou a memória da IA; religando o modelo (já está baixado)…");
        const id = this.modelo;
        this.engine = null;
        await this.carregar(id);
        return this._gerar(mensagens, aoReceber);
      }
      throw e;
    }
  }

  async descarregar() {
    if (this.engine?.unload) await this.engine.unload();
    this.engine = null; this.modelo = null;
  }
}
