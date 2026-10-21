// Cérebros na nuvem com as SUAS chaves de API (Gemini, OpenAI, Groq, OpenRouter, NVIDIA/Brave por proxy, ou qualquer serviço compatível com OpenAI).
// A chave fica só neste aparelho (IndexedDB, fora da cópia de segurança) e só é enviada ao provedor que você escolheu.
// Limite: a NVIDIA e o Brave não liberam chamadas direto do navegador (sem CORS); use um proxy seu (veja docs/CELULAR-INDEPENDENTE.md).
// Cada provedor usa o LEQUE inteiro de modelos de conversa: pula os encerrados (404/410) e lembra o que já funcionou.
import { EstadoLeque, MAX_TENTATIVAS, ordenar } from "./leque.js";
import { mensagensParaTexto } from "./uso.js";

export const PROVEDORES = {
  gemini: { nome: "Google Gemini", base: "https://generativelanguage.googleapis.com/v1beta/openai", modelo: "gemini-flash-latest", dica: "Chave grátis em aistudio.google.com/apikey" },
  openai: { nome: "OpenAI", base: "https://api.openai.com/v1", modelo: "gpt-4o-mini", dica: "Chave em platform.openai.com/api-keys" },
  groq: { nome: "Groq", base: "https://api.groq.com/openai/v1", modelo: "llama-3.3-70b-versatile", dica: "Chave grátis em console.groq.com/keys" },
  openrouter: { nome: "OpenRouter", base: "https://openrouter.ai/api/v1", modelo: "meta-llama/llama-3.3-70b-instruct:free", dica: "Chave em openrouter.ai/keys (tem modelos grátis)" },
  brave: { nome: "Brave Search (por proxy)", base: "", modelo: "", tipo: "busca", dica: "Busca na web. O Brave bloqueia o navegador: a URL base é a do SEU proxy, SEM /v1 (veja o passo a passo abaixo)", exigeBase: true },
  nvidia: { nome: "NVIDIA (por proxy)", base: "", modelo: "nvidia/llama-3.1-nemotron-70b-instruct", dica: "A NVIDIA bloqueia o navegador: a URL base é a do SEU proxy COM /v1 no fim (veja o passo a passo abaixo)", exigeBase: true },
  personalizado: { nome: "Outro (compatível com OpenAI)", base: "", modelo: "", dica: "Informe a URL base (…/v1) e o modelo", exigeBase: true },
};
const SEGREDO = "segredo:";
const nomeDe = (id) => PROVEDORES[id]?.nome || id;

export class Nuvem {
  constructor({ armazem, buscar = (...a) => fetch(...a), agora = () => Date.now(), aoUsar = null }) {
    this.aoUsar = aoUsar;  // opcional: (fonte, { entrada, saida, textoEntrada, textoSaida }) para os contadores locais de uso
    this.armazem = armazem; this.buscar = buscar; this.leque = new EstadoLeque(armazem, agora);
  }

  async salvas() {
    const chaves = (await this.armazem.chaves()).filter((c) => c.startsWith(SEGREDO));
    return Promise.all(chaves.map(async (c) => { const s = await this.armazem.ler(c); return { id: c.slice(SEGREDO.length), nome: nomeDe(s.provedor), modelo: s.modelo, provedor: s.provedor }; }));
  }

  async remover(id) { await this.armazem.apagar(SEGREDO + id); await this.armazem.apagar("leque:" + id); }
  async configurada() { return (await this._segredos()).length > 0; }

  // Só os provedores de CONVERSA (o Brave é busca, não responde perguntas).
  async _segredos() {
    const todos = await Promise.all((await this.armazem.chaves()).filter((c) => c.startsWith(SEGREDO)).map((c) => this.armazem.ler(c)));
    return todos.filter((s) => PROVEDORES[s.provedor]?.tipo !== "busca");
  }

  // Chave e proxy do Brave Search, se o usuário cadastrou.
  async brave() { const s = await this.armazem.ler(SEGREDO + "brave"); return s ? { chave: s.chave, base: s.base } : null; }

  // Chave do Gemini cadastrada (para a voz do Gemini em voz-gemini.js), ou null. Nunca vai para log nem para a cópia de segurança.
  async chaveGemini() { const s = await this.armazem.ler(SEGREDO + "gemini"); return s?.chave || null; }

  _cabecalhos(chave) { return { Authorization: `Bearer ${chave}`, "Content-Type": "application/json" }; }

  async _listar(base, chave) {
    const r = await this.buscar(`${base}/models`, { headers: this._cabecalhos(chave) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return ((await r.json()).data || []).map((m) => String(m.id).replace(/^models\//, ""));
  }

  // Relê o catálogo do provedor e guarda TODOS os modelos de conversa. Sem permissão ou sem rede, mantém o que já tinha.
  async _atualizarPool(s) {
    try { await this.leque.definirPool(s.provedor, ordenar(s.provedor, await this._listar(s.base, s.chave))); } catch { /* o leque é uma otimização */ }
  }

  async _pedir(base, chave, modelo, mensagens, aoReceber, medida = {}) {
    const r = await this.buscar(`${base}/chat/completions`, { method: "POST", headers: this._cabecalhos(chave),
      body: JSON.stringify({ model: modelo, messages: mensagens, stream: Boolean(aoReceber), max_tokens: 900, temperature: 0.5 }) });
    if (!r.ok) {
      const corpo = await r.text().catch(() => "");
      const erro = new Error(r.status === 401 || r.status === 403 ? "chave recusada pelo provedor" : r.status === 404 || r.status === 410 ? "modelo não encontrado" : r.status === 429 ? "limite de uso atingido" : `HTTP ${r.status} ${corpo.slice(0, 120)}`);
      erro.status = r.status;
      throw erro;
    }
    if (!aoReceber || !r.body) {
      const corpo = await r.json();
      medida.usage = corpo.usage;
      return (corpo.choices?.[0]?.message?.content || "").trim();
    }
    let texto = "", resto = "";
    const leitor = r.body.getReader(), decodificador = new TextDecoder();
    for (;;) {
      const { done, value } = await leitor.read();
      if (done) break;
      resto += decodificador.decode(value, { stream: true });
      const linhas = resto.split("\n");
      resto = linhas.pop();
      for (const linha of linhas) {
        const dado = linha.replace(/^data:\s*/, "").trim();
        if (!linha.startsWith("data:") || !dado || dado === "[DONE]") continue;
        try { const pedaco = JSON.parse(dado); if (pedaco.usage) medida.usage = pedaco.usage; texto += pedaco.choices?.[0]?.delta?.content || ""; aoReceber(texto); } catch { /* pedaço incompleto */ }
      }
    }
    return texto.trim();
  }

  // Conta a chamada nos contadores locais (tokens do provedor quando vierem; senão estimados). Nunca atrapalha a resposta.
  _contar(fonte, mensagens, texto, usage) {
    try {
      this.aoUsar?.(fonte, { entrada: usage?.prompt_tokens, saida: usage?.completion_tokens, textoEntrada: mensagensParaTexto(mensagens), textoSaida: texto });
    } catch { /* contador é opcional */ }
  }

  // Tenta os modelos do leque em ordem (o último que funcionou primeiro) e fica com o primeiro que responder.
  // 404/410/400 = modelo encerrado: ignora por 3 dias. Chave recusada para tudo; limite de uso para depois de 2 modelos.
  async _comLeque(s, mensagens, aoReceber) {
    if (!(await this.leque.pool(s.provedor)).length) await this._atualizarPool(s);
    const falhas = [], tentados = new Set();
    let limites = 0, erros = 0;
    for (let rodada = 0; rodada < 2; rodada++) {
      for (const modelo of (await this.leque.ordem(s.provedor, s.modelo)).filter((m) => !tentados.has(m)).slice(0, MAX_TENTATIVAS)) {
        tentados.add(modelo);
        try {
          const medida = {}, texto = await this._pedir(s.base, s.chave, modelo, mensagens, aoReceber, medida);
          if (!texto) { falhas.push(`${modelo}: resposta vazia`); continue; }
          this._contar(s.provedor, mensagens, texto, medida.usage);
          await this.leque.marcarBom(s.provedor, modelo);
          if (modelo !== s.modelo) { s.modelo = modelo; await this.armazem.gravar(SEGREDO + s.provedor, s); }
          return { texto, modelo };
        } catch (e) {
          if (e instanceof TypeError) throw new Error("sem conexão com o provedor (ou o navegador bloqueou: a NVIDIA e o Brave só funcionam por proxy)");
          if (e.message === "chave recusada pelo provedor") throw e;
          if (e.message === "modelo não encontrado" || e.status === 400) await this.leque.marcarMorto(s.provedor, modelo);
          else if (e.message === "limite de uso atingido") limites++;
          else erros++;
          falhas.push(`${modelo}: ${e.message}`);
          if (limites >= 2 || erros >= 4) throw new Error(falhas.slice(-2).join("; "));
        }
      }
      if (rodada === 0) await this._atualizarPool(s);  // esgotou o leque: relê o catálogo e tenta só os que ainda não foram tentados
    }
    throw new Error("nenhum modelo respondeu (" + falhas.slice(-3).join("; ") + ")");
  }

  // Testa a chave com uma pergunta mínima, passando pelo leque, e só então guarda (a chave nunca é gravada se não funcionar).
  async salvar(provedor, chave, { base = "", modelo = "" } = {}) {
    const p = PROVEDORES[provedor];
    chave = String(chave).replace(/\s+/g, "");
    if (!p) throw new Error("provedor desconhecido");
    if (chave.length < 16) throw new Error("isso não parece uma chave de API (muito curta)");
    const url = (base || p.base).replace(/\/+$/, "");
    if (!/^https:\/\//.test(url)) throw new Error("a URL base precisa começar com https://");
    if (p.tipo === "busca") {  // Brave: testa com uma busca de verdade
      let r;
      try { r = await this.buscar(`${url}/brave/res/v1/web/search?q=teste&count=1`, { headers: { "X-Subscription-Token": chave, Accept: "application/json" } }); }
      catch { throw new Error("não consegui falar com o proxy (confira a URL do seu proxy)"); }
      if (!r.ok) throw new Error(r.status === 401 || r.status === 403 ? "chave do Brave recusada" : `o Brave respondeu ${r.status}`);
      await this.armazem.gravar(SEGREDO + provedor, { provedor, chave, base: url, modelo: "busca" });
      return "busca na web";
    }
    const s = { provedor, chave, base: url, modelo: modelo || p.modelo };
    const resposta = await this._comLeque(s, [{ role: "user", content: "Responda apenas: ok" }]);
    await this.armazem.gravar(SEGREDO + provedor, { ...s, modelo: resposta.modelo });
    return resposta.modelo;
  }

  // Tenta os provedores salvos, um a um; erro ou limite de uso passa para o próximo. Devolve { texto, provedor, modelo }.
  async perguntar(mensagens, aoReceber) {
    const falhas = [];
    for (const s of await this._segredos()) {
      try {
        const r = await this._comLeque(s, mensagens, aoReceber);
        return { texto: r.texto, provedor: nomeDe(s.provedor), modelo: r.modelo };
      } catch (e) { falhas.push(`${s.provedor}: ${e.message}`); }
    }
    throw new Error(falhas.length ? falhas.join("; ") : "nenhuma chave de API cadastrada");
  }
}
