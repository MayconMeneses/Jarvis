// "Ler para mim": texto (ou artigo completo) -> idioma -> tradução para pt-BR -> fala em partes de até 350 caracteres, com parar e continuar.
// Uma leitura por vez. Estados: parado, baixando, traduzindo, lendo. O texto é dado de terceiros: só é falado, nada do que ele diz vira ação.
// Porte de jarvis/info/leitor.py (no lugar de thread, cada etapa confere se ainda é a leitura atual).
import { NOMES, detectar } from "./leitor-idioma.js";
import { RESUMO_MAX, TEXTO_MAX, partes, resumir } from "./leitor-partes.js";
import { SemCerebro } from "./leitor-traducao.js";
import { limparMarcacao } from "./voz-normalizar.js";
import { limparParaFala } from "./voz-texto.js";

export const AVISO_ORIGINAL = "Atenção: vou ler no idioma original com a voz do aparelho para esse idioma; a pronúncia pode sair estranha.";
const ITEM_VAZIO = { titulo: "", trecho: "", url: "", completo: false, idioma: "", original: false, resumir: false };

export class Leitor {
  // fala: criarFala(). baixar(url) -> { texto, idioma } (Worker /ler). tradutor: Tradutor. aoMudar(estado) para a tela.
  constructor({ fala, baixar = null, tradutor = null, aoMudar = () => {} }) {
    Object.assign(this, { fala, baixarFn: baixar, tradutor, aoMudar, _token: 0, _restante: [], _lang: "pt", _aviso: "", _tarefa: Promise.resolve() });
    this._st = this._novo("parado", "");
  }

  _novo(estado, mensagem, extra = {}) {
    return { estado, mensagem, idioma: "", parte: 0, total: 0, podeContinuar: false, oferecerOriginal: false, quemTraduziu: "", ...extra };
  }
  _set(estado, mensagem = "", extra = {}) {
    const ant = this._st;
    this._st = this._novo(estado, mensagem, { idioma: ant.idioma, total: ant.total, quemTraduziu: ant.quemTraduziu, ...extra });
    try { this.aoMudar(this.estado()); } catch { /* a tela nunca derruba a leitura */ }
  }

  estado() { return { ...this._st }; }
  ocupado() { return ["baixando", "traduzindo", "lendo"].includes(this._st.estado); }
  fim() { return this._tarefa; }  // para os testes: espera a leitura atual terminar

  // Corta a fala e a preparação; o que sobrou (inclusive a parte cortada) fica para `continuar`.
  parar() {
    this._token++;
    this.fala.parar();
    this.fala.manterAcesa?.(false);
    if (this._st.estado !== "parado") this._set("parado", "Leitura parada.", { parte: this._st.parte, podeContinuar: this._restante.length > 0 });
    return this.estado();
  }

  // Começa a ler `item`. Para qualquer leitura anterior primeiro.
  iniciar(item, { atrasoMs = 0 } = {}) {  // atrasoMs: deixa a resposta do chat ser falada antes da primeira parte
    item = { ...ITEM_VAZIO, ...item };
    this.parar();
    this._restante = [];
    const token = this._token;
    this._set(item.completo && item.url && this.baixarFn ? "baixando" : "traduzindo", "Preparando a leitura…", { idioma: "" });
    this._atraso = atrasoMs;
    this._tarefa = this._trabalho(item, token);
    return this.estado();
  }

  continuar() {
    if (!this._restante.length || this.ocupado()) return this.estado();
    const token = ++this._token;
    this._tarefa = this._falarPartes([...this._restante], token);
    return this.estado();
  }

  async _trabalho(item, token) {
    try {
      const { texto, idioma } = await this._obterTexto(item);
      if (token !== this._token) return;
      const lista = await this._preparar(texto, idioma, item, token);
      if (lista && token === this._token) await this._falarPartes(lista, token);
    } catch {
      if (token === this._token) this._set("parado", "Não consegui ler isso agora.");
    }
  }

  async _obterTexto(item) {
    const base = [item.titulo, item.trecho].filter(Boolean).join(" ").trim();
    this._aviso = "";
    if (item.completo && item.url && this.baixarFn) {
      try {
        const lido = await this.baixarFn(item.url);
        return { texto: lido.texto, idioma: lido.idioma || "" };
      } catch { this._aviso = "Não consegui baixar o artigo. Vou ler só o resumo do cartão."; }
    } else if (item.completo && item.url) this._aviso = "Sem o Worker não consigo baixar o artigo. Vou ler só o resumo do cartão.";
    return { texto: base, idioma: "" };
  }

  async _preparar(texto, idiomaLido, item, token) {
    const idioma = NOMES[item.idioma] ? item.idioma : NOMES[idiomaLido] ? idiomaLido : detectar(texto);
    texto = texto.slice(0, TEXTO_MAX);
    const pre = this._aviso ? [this._aviso] : [];
    this._lang = "pt";
    if (idioma !== "pt") {
      this._set("traduzindo", `Traduzindo do ${NOMES[idioma]}…`, { idioma });
      try {
        if (!this.tradutor) throw new SemCerebro();
        texto = await this.tradutor.traduzir(texto, idioma);
        this._st.quemTraduziu = this.tradutor.ultimo;
      } catch (e) {
        if (!(e instanceof SemCerebro) || token !== this._token) { if (token === this._token) throw e; return null; }
        if (!item.original) {
          this._set("parado", `O texto está em ${NOMES[idioma]} e não há tradutor disponível (cérebro de IA ou internet). Posso ler no idioma original.`, { idioma, oferecerOriginal: true });
          return null;
        }
        pre.push(AVISO_ORIGINAL);
        this._lang = idioma;
      }
    }
    if (item.resumir) texto = resumir(texto, RESUMO_MAX);
    return [...partes(pre.join(" ")).map((t) => [t, "pt"]), ...partes(texto).map((t) => [t, this._lang])];  // [texto, idioma da voz]
  }

  async _falarPartes(lista, token) {
    const total = lista.length;
    this.fala.manterAcesa?.(true);
    if (this._atraso) { const a = this._atraso; this._atraso = 0; await (this.fala.esperar?.(a)); }
    for (let i = 0; i < total; i++) {
      if (token !== this._token) return;
      this._restante = lista.slice(i);  // a parte interrompida volta a ser lida no "continuar"
      this._set("lendo", "", { parte: i + 1, total });
      const [texto, idioma] = lista[i];
      await this.fala.falar(idioma === "pt" ? limparParaFala(texto) : limparMarcacao(texto), { idioma });
    }
    if (token !== this._token) return;
    this._restante = [];
    this.fala.manterAcesa?.(false);
    this._set("parado", "Leitura concluída.", { parte: total, total });
  }
}
