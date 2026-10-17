// Cérebros na nuvem com as SUAS chaves de API (Gemini, OpenAI, Groq, OpenRouter ou qualquer serviço compatível com OpenAI).
// A chave fica só neste aparelho (IndexedDB, fora da cópia de segurança) e só é enviada ao provedor que você escolheu.
// Limite: a NVIDIA não libera chamadas direto do navegador (sem CORS); para ela use um proxy seu (veja docs/CELULAR-INDEPENDENTE.md).
import { fold } from "./util.js";

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
const PULAR_AO_LISTAR = ["embed", "guard", "safety", "reward", "vision", "tts", "audio", "image", "whisper", "moderation", "rerank", "dall-e", "transcribe", "realtime"];

export class Nuvem {
  constructor({ armazem, buscar = (...a) => fetch(...a) }) { this.armazem = armazem; this.buscar = buscar; }

  async salvas() {
    const chaves = (await this.armazem.chaves()).filter((c) => c.startsWith(SEGREDO));
    return Promise.all(chaves.map(async (c) => { const s = await this.armazem.ler(c); return { id: c.slice(SEGREDO.length), nome: PROVEDORES[s.provedor]?.nome || s.provedor, modelo: s.modelo, provedor: s.provedor }; }));
  }

  async remover(id) { await this.armazem.apagar(SEGREDO + id); }
  async configurada() { return (await this._segredos()).length > 0; }

  // Só os provedores de CONVERSA (o Brave é busca, não responde perguntas).
  async _segredos() {
    const todos = await Promise.all((await this.armazem.chaves()).filter((c) => c.startsWith(SEGREDO)).map((c) => this.armazem.ler(c)));
    return todos.filter((s) => PROVEDORES[s.provedor]?.tipo !== "busca");
  }

  // Chave e proxy do Brave Search, se o usuário cadastrou.
  async brave() { const s = await this.armazem.ler(SEGREDO + "brave"); return s ? { chave: s.chave, base: s.base } : null; }

  _cabecalhos(chave) { return { Authorization: `Bearer ${chave}`, "Content-Type": "application/json" }; }

  async _listar(base, chave) {
    const r = await this.buscar(`${base}/models`, { headers: this._cabecalhos(chave) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return ((await r.json()).data || []).map((m) => String(m.id).replace(/^models\//, ""));
  }

  // O catálogo muda (modelos aposentados): se o modelo padrão não existe, escolhe um de conversa que a chave enxerga.
  async _escolherModelo(base, chave, preferido) {
    const todos = (await this._listar(base, chave)).filter((m) => !PULAR_AO_LISTAR.some((p) => fold(m).includes(p)));
    if (preferido && todos.includes(preferido)) return preferido;
    const flash = todos.filter((m) => /gemini/.test(m) && /flash/.test(m) && !/lite|image|preview|exp|thinking/.test(m));
    if (flash.length) return flash.sort((a, b) => parseFloat((b.match(/\d+(\.\d+)?/) || [0])[0]) - parseFloat((a.match(/\d+(\.\d+)?/) || [0])[0]))[0];
    const conversa = todos.filter((m) => /instruct|chat|-it|versatile|gpt|llama|mistral|gemma|qwen/.test(fold(m)));
    if (!(conversa[0] || todos[0])) throw new Error("nenhum modelo de conversa disponível para esta chave");
    return conversa[0] || todos[0];
  }

  async _pedir(base, chave, modelo, mensagens, aoReceber) {
    const r = await this.buscar(`${base}/chat/completions`, { method: "POST", headers: this._cabecalhos(chave),
      body: JSON.stringify({ model: modelo, messages: mensagens, stream: Boolean(aoReceber), max_tokens: 900, temperature: 0.5 }) });
    if (!r.ok) {
      const corpo = await r.text().catch(() => "");
      const erro = new Error(r.status === 401 || r.status === 403 ? "chave recusada pelo provedor" : r.status === 404 || r.status === 410 ? "modelo não encontrado" : r.status === 429 ? "limite de uso atingido" : `HTTP ${r.status} ${corpo.slice(0, 120)}`);
      erro.status = r.status;
      throw erro;
    }
    if (!aoReceber || !r.body) return ((await r.json()).choices?.[0]?.message?.content || "").trim();
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
        try { texto += JSON.parse(dado).choices?.[0]?.delta?.content || ""; aoReceber(texto); } catch { /* pedaço incompleto */ }
      }
    }
    return texto.trim();
  }

  // Testa a chave com uma pergunta mínima e só então guarda (a chave nunca é gravada se não funcionar).
  async salvar(provedor, chave, { base = "", modelo = "" } = {}) {
    const p = PROVEDORES[provedor];
    chave = String(chave).replace(/\s+/g, "");
    if (!p) throw new Error("provedor desconhecido");
    if (chave.length < 16) throw new Error("isso não parece uma chave de API (muito curta)");
    const url = (base || p.base).replace(/\/+$/, "");
    if (!/^https:\/\//.test(url)) throw new Error("a URL base precisa começar com https://");
    if (p.tipo === "busca") {  // Brave: testa com uma busca de verdade
      const r = await this.buscar(`${url}/brave/res/v1/web/search?q=teste&count=1`, { headers: { "X-Subscription-Token": chave, Accept: "application/json" } }).catch(() => { throw new Error("não consegui falar com o proxy (confira a URL do seu proxy)"); });
      if (!r.ok) throw new Error(r.status === 401 || r.status === 403 ? "chave do Brave recusada" : `o Brave respondeu ${r.status}`);
      await this.armazem.gravar(SEGREDO + provedor, { provedor, chave, base: url, modelo: "busca" });
      return "busca na web";
    }
    let escolhido = modelo || p.modelo;
    const teste = [{ role: "user", content: "Responda apenas: ok" }];
    try {
      await this._pedir(url, chave, escolhido, teste);
    } catch (e) {
      const modeloRuim = e.message === "modelo não encontrado" || e.status === 400;  // nome de modelo aposentado ou inválido
      if (!modeloRuim) {
        if (e instanceof TypeError) throw new Error("não consegui falar com o provedor (o navegador bloqueou ou está sem internet; a NVIDIA, por exemplo, só funciona por proxy)");
        throw e;
      }
      escolhido = await this._escolherModelo(url, chave, "");  // o modelo padrão saiu do catálogo: acha outro que responda
      await this._pedir(url, chave, escolhido, teste);
    }
    await this.armazem.gravar(SEGREDO + provedor, { provedor, chave, base: url, modelo: escolhido });
    return escolhido;
  }

  // Tenta os provedores salvos, um a um; limite de uso e erro passam para o próximo. Devolve { texto, provedor }.
  async perguntar(mensagens, aoReceber) {
    const falhas = [];
    for (const s of await this._segredos()) {
      try {
        const texto = await this._pedir(s.base, s.chave, s.modelo, mensagens, aoReceber);
        if (texto) return { texto, provedor: PROVEDORES[s.provedor]?.nome || s.provedor };
        falhas.push(`${s.provedor}: resposta vazia`);
      } catch (e) {
        if (e.message === "modelo não encontrado") {  // aposentado depois de salvar: reescolhe e tenta uma vez
          try {
            s.modelo = await this._escolherModelo(s.base, s.chave, "");
            await this.armazem.gravar(SEGREDO + s.provedor, s);
            const texto = await this._pedir(s.base, s.chave, s.modelo, mensagens, aoReceber);
            if (texto) return { texto, provedor: PROVEDORES[s.provedor]?.nome || s.provedor };
          } catch (e2) { falhas.push(`${s.provedor}: ${e2.message}`); continue; }
        }
        falhas.push(`${s.provedor}: ${e instanceof TypeError ? "sem conexão ou bloqueado pelo navegador" : e.message}`);
      }
    }
    throw new Error(falhas.length ? falhas.join("; ") : "nenhuma chave de API cadastrada");
  }
}
