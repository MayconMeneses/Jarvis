// PC pareado (opcional, SOMENTE LEITURA): o Jarvis do PC entrega agenda, e-mails, bom dia e agentes ao celular.
// O token do pareamento fica só no IndexedDB deste aparelho (chave "pc:pareado", fora da cópia de segurança). Nada é enviado ao PC além do pedido de leitura.
import { validarResposta } from "./pc-validar.js";
const CHAVE = "pc:pareado";
const MAX_RESPOSTA = 2_000_000;
const CACHE = "pc:cache:";
const ROTAS = { agenda: "/api/agenda", emails: "/api/emails", briefing: "/api/briefing", agentes: "/api/agents" };
export const OFFLINE = "PC desligado ou fora da rede.";

// Só https (o app é https; http seria bloqueado pelo navegador e passaria o token sem criptografia). Devolve só a origem.
export function normalizarUrl(texto) {
  let u;
  try { u = new URL(String(texto).trim()); } catch { throw new Error("endereço inválido; use algo como https://seu-pc.tailnet.ts.net:8765"); }
  if (u.protocol !== "https:") throw new Error("o endereço precisa começar com https:// (use o endereço do Tailscale que a janela do PC mostra)");
  if (u.username || u.password) throw new Error("endereço inválido");
  return u.origin;
}

export class PcPareado {
  constructor({ armazem, buscar = (...a) => fetch(...a), agora = () => new Date(), timeoutMs = 8000 }) {
    Object.assign(this, { armazem, buscar, agora, timeoutMs });
  }

  async pareamento() { return (await this.armazem.ler(CHAVE)) || null; }
  async pareado() { return Boolean(await this.pareamento()); }

  async _chamar(url, opcoes = {}) {
    const ctl = new AbortController(), t = setTimeout(() => ctl.abort(), this.timeoutMs);
    try { return await this.buscar(url, { ...opcoes, signal: ctl.signal, cache: "no-store", credentials: "omit" }); } finally { clearTimeout(t); }
  }

  // Troca o código de 6 dígitos (gerado na janela do PC, "Jarvis no celular") por um token. O token nunca aparece na tela.
  async parear(endereco, codigo, nome = "Jarvis do celular") {
    const url = normalizarUrl(endereco), cod = String(codigo).trim();
    if (!/^\d{6}$/.test(cod)) throw new Error("o código tem 6 dígitos");
    let r;
    try { r = await this._chamar(url + "/api/parear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ codigo: cod, nome }) }); }
    catch { throw new Error(OFFLINE); }
    if (!r.ok) throw new Error(r.status === 403 ? "código inválido, vencido ou bloqueado; gere outro na janela do PC" : `o PC respondeu HTTP ${r.status}`);
    const { token } = (await r.json()) || {};
    if (typeof token !== "string" || !token || token.length > 512 || /[^!-~]/.test(token)) throw new Error("resposta inesperada do PC");
    await this.armazem.gravar(CHAVE, { url, token, desde: this.agora().toISOString() });
    return url;
  }

  async desparear() {
    await this.armazem.apagar(CHAVE);
    for (const rota of Object.keys(ROTAS)) await this.armazem.apagar(CACHE + rota);
  }

  // Lê uma rota. Devolve { ok, dados, quando, doCache, erro }. Offline ou erro do PC: a última resposta guardada, marcada com a hora.
  async obter(rota) {
    const p = await this.pareamento();
    if (!p) return { ok: false, erro: "Pareie com o PC na aba Cérebro para ver isto." };
    let erro = OFFLINE;
    try {
      const r = await this._chamar(p.url + ROTAS[rota], { headers: { Authorization: `Bearer ${p.token}` } });
      if (r.ok) {
        if (Number(r.headers?.get?.("content-length")) > MAX_RESPOSTA) throw new Error("resposta grande demais");
        const dados = validarResposta(rota, await r.json()), quando = this.agora().toISOString();
        if (!dados) erro = "O PC respondeu algo inesperado.";
        else { await this.armazem.gravar(CACHE + rota, { quando, dados }); return { ok: true, dados, quando, doCache: false }; }
      } else erro = r.status === 401 ? "O PC não reconhece mais este celular. Pareie de novo." : "O PC não conseguiu ler agora.";
    } catch { /* sem rede, PC desligado ou tempo esgotado */ }
    const guardado = await this.armazem.ler(CACHE + rota), limpo = guardado && validarResposta(rota, guardado.dados);
    if (guardado) guardado.dados = limpo;
    return limpo ? { ok: true, dados: guardado.dados, quando: guardado.quando, doCache: true, erro } : { ok: false, erro };
  }
}
