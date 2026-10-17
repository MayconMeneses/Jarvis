// Conversa contínua: o histórico fica salvo no aparelho (sobrevive a fechar o app) e o que vai para o modelo respeita o limite dele.
// Causa do "a conversa encerra depois de 3 perguntas": respostas longas (código) enchiam o contexto de 4096 tokens do modelo.
import { cortar } from "./util.js";

const CHAVE = "conversa";
export const MAX_SALVAS = 60;
export const LIMITE_HISTORICO_CHARS = 2600;  // ~800 tokens: sobra espaço para o prompt de sistema (~1000) e a resposta (600)
export const LIMITE_RESPOSTA_ANTIGA = 280;   // respostas antigas viram resumos de uma linha no contexto do modelo

export class Conversa {
  constructor(memoria, relogio = () => Date.now()) { this.memoria = memoria; this.relogio = relogio; this.itens = []; }

  async carregar() {
    const salvas = await this.memoria.meta(CHAVE);
    this.itens = Array.isArray(salvas) ? salvas.filter((m) => m && (m.role === "user" || m.role === "assistant") && typeof m.content === "string") : [];
    return this.itens;
  }

  async adicionar(role, content) {
    const texto = String(content || "").trim();
    if (!texto) return;  // resposta vazia (erro) nunca entra: quebraria a alternância user/assistant do modelo
    this.itens.push({ role, content: texto.slice(0, 4000), em: this.relogio() });
    this.itens = this.itens.slice(-MAX_SALVAS);
    await this.memoria.definirMeta(CHAVE, this.itens);
  }

  async limpar() { this.itens = []; await this.memoria.definirMeta(CHAVE, null); }

  // Mensagens para o modelo: as mais recentes que cabem no limite, começando sempre por uma fala do usuário e alternando papéis.
  paraPrompt(limite = LIMITE_HISTORICO_CHARS) {
    const lista = [];
    let total = 0;
    for (let i = this.itens.length - 1; i >= 0; i--) {
      const m = this.itens[i];
      const ultima = i === this.itens.length - 1;
      const conteudo = m.role === "assistant" && !ultima ? cortar(m.content.replace(/```[\s\S]*?```/g, "[código]").replace(/\s+/g, " "), LIMITE_RESPOSTA_ANTIGA) : cortar(m.content, 1200);
      if (total + conteudo.length > limite && lista.length) break;
      total += conteudo.length;
      lista.unshift({ role: m.role, content: conteudo });
    }
    while (lista.length && lista[0].role !== "user") lista.shift();
    return lista.filter((m, i) => i === 0 || m.role !== lista[i - 1].role);  // sem dois papéis iguais seguidos
  }
}
