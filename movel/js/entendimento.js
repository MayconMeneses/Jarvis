// Entendimento sem IA: fica ENTRE as regras exatas do motor e o "não entendi". Casa a frase com os comandos e com o autoconhecimento
// (índice BM25 + exemplos + trigramas + correção de digitação) e decide pela confiança:
//   alta  -> responde (e diz como entendeu);  média -> pergunta "Você quis dizer: ...?";  baixa -> admite, mostra as mais próximas e as saídas.
// Também usa o que aprendeu com o usuário (esclarecimentos e atalhos) e conta, só no aparelho, quanto entende (ver aprendizado.js).
import { Aprendizado } from "./aprendizado.js";
import { alvos as alvosDoApp, formatar } from "./autoconhecimento.js";
import { ALVOS_COMANDOS, SOMENTE_LEITURA } from "./intencao-comandos.js";
import { Indice } from "./intencao-indice.js";
import { lerEnsinamento, respostaCurta } from "./ensinar.js";
import { cortar } from "./util.js";

// Mesmos limiares do PC (jarvis/local/casador.py). `amplo`: nota mínima para o autoconhecimento passar na frente de uma regra genérica.
export const LIMIARES = { alta: 0.62, media: 0.4, margem: 0.08, amplo: 0.75 };
const MAX_FRASE = 200;

export class Entendimento {
  constructor({ memoria, entradas = [], aparelho = {}, estado = async () => ({}), executar = async () => null, classificar = () => null, temIA = async () => false, relogio }) {
    Object.assign(this, { aparelho, estado, executar, classificar, temIA });
    this.aprend = new Aprendizado(memoria, relogio);
    this.definirEntradas(entradas);
    this.pendente = null;   // opções do último "você quis dizer" (para responder só "sim" ou "2")
    this.widget = null;     // botões/cartão que a tela mostra junto da resposta (ver entendimento-ui.js)
  }

  definirEntradas(entradas, aprendidas = []) {
    this.entradas = new Map(entradas.map((e) => [e.id, e]));
    const extra = new Map();  // frases que o usuário já esclareceu viram exemplos do alvo escolhido (a Jarvis "evolui" sem IA)
    for (const { t, id } of aprendidas) extra.set(id, [...(extra.get(id) || []), t]);
    this.indice = new Indice([...ALVOS_COMANDOS, ...alvosDoApp(entradas)].map((a) => (extra.has(a.id) ? { ...a, exemplos: [...a.exemplos, ...extra.get(a.id)] } : a)));
  }

  // Carrega o que foi aprendido em conversas anteriores. Chamado uma vez ao abrir o app.
  async iniciar() { this.definirEntradas([...this.entradas.values()], (await this.aprend.resumo()).escolhas); return this; }

  tomarWidget() { const w = this.widget; this.widget = null; return w; }

  // Ordena os candidatos e diz o nível de confiança.
  ranquear(frase) {
    const lista = this.indice.buscar(frase, 5), topo = lista[0];
    if (!topo) return { nivel: "baixa", lista };
    const margem = topo.nota - (lista[1]?.nota ?? 0);
    return { nivel: topo.nota >= LIMIARES.alta && margem >= LIMIARES.margem ? "alta" : topo.nota >= LIMIARES.media ? "media" : "baixa", lista, topo, margem };
  }

  // Antes das regras: respostas curtas ("sim", "2"), ensinamentos e atalhos do usuário. Devolve { texto, resposta }.
  async preparar(texto) {
    const t = String(texto || "");
    if (this.pendente) {
      const pend = this.pendente, curta = respostaCurta(t);
      this.pendente = null;
      if (curta === -1) return { texto: t, resposta: "Tudo bem. Reformule o pedido com outras palavras, ou diga \"isso significa ...\" para eu aprender." };
      if (curta !== null && pend.opcoes[curta]) return { texto: t, resposta: (await this.escolher(pend.frase, pend.opcoes[curta].id)).texto };
    }
    const ensino = lerEnsinamento(t);
    if (ensino) {
      const resposta = await this._proporAtalho(ensino);
      if (resposta) return { texto: t, resposta };
    }
    if (t.length <= MAX_FRASE) {
      const para = await this.aprend.apelidoPara(t), alvo = para && await this.resolverDestino(para);  // revalida: só leitura, sempre
      if (alvo) return { texto: t, resposta: await this.responderAlvo(alvo, para, "ok") };  // roda a frase PADRÃO do comando, nunca o texto digitado
    }
    return { texto: t };
  }

  async _proporAtalho(ensino) {
    const de = ensino.deAnterior ? await this.aprend.ultimaFalha() : ensino.de;
    if (!de) return "Não sei de qual frase você fala. Diga assim: \"quando eu disser bom dia chefe, mostre minha agenda\".";
    const destino = await this.resolverDestino(ensino.para);
    if (!destino) return ensino.explicito ? `Não achei um comando de leitura parecido com "${ensino.para}". Eu só ligo atalhos a coisas como hora, agenda, notícias, clima ou explicações do app. Tente de outro jeito.` : null;
    if (await this.classificar(de)) return `Já entendo "${de}" sozinha (é um comando meu), então não preciso de atalho.`;
    this.widget = { tipo: "proposta", de, para: ensino.para, destino: destino.rotulo };
    return `Posso guardar este atalho?\n\nQuando você disser **“${de}”**, eu entendo como **“${ensino.para}”** (${destino.rotulo}).\n\nSó vale neste aparelho e você pode apagar quando quiser.`;
  }

  // A frase de destino precisa levar a um assunto do app ou a um comando que só LÊ. Devolve o alvo ou null.
  async resolverDestino(frase) {
    const direta = await this.classificar(frase);
    if (direta) { const alvo = ALVOS_COMANDOS.find((a) => a.id === direta); return alvo && SOMENTE_LEITURA.has(direta) ? alvo : null; }
    const r = this.ranquear(frase);
    if (!r.topo || r.nivel === "baixa") return null;
    return r.topo.tipo === "app" || SOMENTE_LEITURA.has(r.topo.id) ? r.topo.alvo : null;
  }

  async confirmarAtalho({ de, para }) {
    try { await this.aprend.gravarApelido({ de, para }, async (p) => Boolean(await this.resolverDestino(p))); return `Guardado: “${de}” agora vale como “${para}”.`; }
    catch (e) { return `Não guardei: ${e.message}.`; }
  }

  // Chamado para frases que nenhuma regra pegou. `amplo`: a regra que casou é genérica (explicar/pesquisar...): só atravessa com confiança alta no app.
  async entender(texto, { amplo = false } = {}) {
    const t = String(texto || "").trim();
    if (t.length < 3 || t.length > MAX_FRASE || t.includes("\n")) return null;
    if (!amplo) {
      const id = await this.aprend.escolhaPara(t), alvo = id && this.indice.alvos.find((a) => a.id === id);
      if (alvo) return this.responderAlvo(alvo, t, "ok");
    }
    const r = this.ranquear(t);
    if (amplo) return r.topo && r.topo.tipo === "app" && r.nivel === "alta" && r.topo.nota >= LIMIARES.amplo ? this.responderAlvo(r.topo.alvo, t, "ok") : null;
    if (r.nivel === "alta") return this.responderAlvo(r.topo.alvo, t, "ok");
    if (r.nivel === "media") return this._perguntar(t, r);
    return null;
  }

  async responderAlvo(alvo, frase, contagem = "ok") {
    await this.aprend.contar(contagem);
    if (alvo.tipo === "app") {
      const e = alvo.entrada, vizinhas = e.relacionados.map((id) => this.entradas.get(id)).filter(Boolean);
      const { texto, botoes } = formatar(e, { aparelho: this.aparelho, frase, estado: await this.estado(), relacionadas: vizinhas });
      this.widget = botoes.length ? { tipo: "botoes", botoes } : null;
      return texto;
    }
    if (!alvo.executar) return `Isso eu sei fazer (**${alvo.rotulo}**), mas preciso de um detalhe. ${alvo.dica}`;
    const resposta = await this.executar(alvo.executar);
    return resposta ? `_Entendi como “${alvo.executar}”._\n\n${resposta}` : `Entendi que você quer **${alvo.rotulo}**, mas não consegui fazer agora. ${alvo.dica}`;
  }

  _perguntar(frase, r) {
    const opcoes = r.lista.filter((x) => x.nota >= LIMIARES.media && x.nota >= r.topo.nota - 0.2).slice(0, 3).map((x) => ({ id: x.id, rotulo: x.alvo.rotulo }));
    this.pendente = { frase, opcoes };
    this.aprend.contar("med").catch(() => {});
    this.widget = { tipo: "escolha", frase, opcoes };
    const lista = opcoes.map((o, i) => `${i + 1}. **${o.rotulo}**`).join("\n");
    return `Você quis dizer:\n${lista}\n\nToque numa opção ou responda "1", "2"${opcoes.length > 2 ? ', "3"' : ""}. Se for outra coisa, fale de outro jeito.`;
  }

  // O usuário escolheu uma opção do "você quis dizer": aprende a frase e responde.
  async escolher(frase, id) {
    const alvo = this.indice.alvos.find((a) => a.id === id);
    if (!alvo) return { texto: "Não encontrei essa opção." };
    await this.aprend.escolha(frase, id);
    this.pendente = null;
    const texto = await this.responderAlvo(alvo, frase, "ok");
    return { texto, widget: this.tomarWidget() };
  }

  // Nenhuma regra, nenhum acerto: admite, mostra as mais próximas e as saídas. Nunca despeja a lista de funções.
  async baixa(frase) {
    await Promise.all([this.aprend.falha(frase), this.aprend.contar("falha")]);
    const r = this.ranquear(frase), perto = r.lista.filter((x) => x.nota >= 0.12).slice(0, 3);
    const opcoes = perto.map((x) => ({ id: x.id, rotulo: x.alvo.rotulo }));
    const botoes = [{ rotulo: "Pesquisar na internet", enviar: `pesquise sobre ${cortar(frase.replace(/[?!.]+$/, ""), 80)}` }];
    this.widget = { tipo: "escolha", frase, opcoes, botoes };
    this.pendente = opcoes.length ? { frase, opcoes } : null;
    const linhas = [`Não entendi “${cortar(frase, 80)}”.`];
    if (opcoes.length) linhas.push("O mais perto que achei:\n" + opcoes.map((o, i) => `${i + 1}. **${o.rotulo}**`).join("\n"));
    linhas.push('Você pode dizer de outro jeito, pedir "pesquise sobre ..." ou me ensinar: "isso significa mostrar minha agenda".');
    return linhas.join("\n\n");
  }

  // Quando a IA assume por baixa confiança, também conta (a evolução mede o cérebro próprio).
  async registrarIA(frase) { await Promise.all([this.aprend.falha(frase), this.aprend.contar("ia")]); }

  // Trechos do autoconhecimento para a IA responder com base neles (dados, não ordens), dentro do limite.
  contextoApp(frase, limite = 900) {
    const usados = this.indice.buscar(frase, 3).filter((x) => x.tipo === "app" && x.nota >= 0.15).slice(0, 2);
    if (!usados.length) return "";
    const blocos = usados.map((x) => { const e = x.alvo.entrada; return `- ${e.titulo}: ${e.resposta} ${e.passos.map((p, i) => `(${i + 1}) ${p}`).join(" ")}`; });
    return cortar(blocos.join("\n"), limite);
  }
}
