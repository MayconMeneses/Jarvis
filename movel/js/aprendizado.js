// Evolução sem IA: a Jarvis anota, SÓ neste aparelho, o que não entendeu, o que você escolheu em "você quis dizer" e os atalhos que você ensinou.
// Nada sai do aparelho e nada disso entra na cópia de segurança (a restauração ignora chaves "evolucao:*"). Tamanhos sempre limitados;
// "apagarTudo" zera tudo. Um atalho ensinado é só uma frase que aponta para um comando de LEITURA já conhecido: nunca vira código nem comando livre.
import { distancia, jaccard, normalizar, trigramas } from "./intencao-texto.js";
import { dataPorExtenso, isoData, semanaIso } from "./util.js";

export const LIMITES = { falhas: 60, escolhas: 60, apelidos: 40, semanas: 12, frase: 120, apelido: 60, alvo: 80 };
const K = { falhas: "evolucao:falhas", escolhas: "evolucao:escolhas", apelidos: "evolucao:apelidos", estat: "evolucao:estat", relatorio: "evolucao:relatorio", ultima: "evolucao:ultima" };
export const CHAVES_EVOLUCAO = Object.values(K);

const limpo = (t, max) => String(t).replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, max);
const semanaDe = (d) => { const [a, s] = semanaIso(d); return `${a}-S${String(s).padStart(2, "0")}`; };
const lista = (v) => (Array.isArray(v) ? v.filter((x) => x && typeof x === "object") : []);

export class Aprendizado {
  constructor(memoria, relogio = () => new Date()) { this.memoria = memoria; this.relogio = relogio; }

  async _ler(k) { return this.memoria.meta(k); }
  async _lista(k) { return lista(await this._ler(k)); }

  // resultado: "ok" (entendi sozinha), "med" (perguntei "você quis dizer"), "falha" (não entendi), "ia" (a IA assumiu)
  async contar(resultado) {
    const e = (await this._ler(K.estat)) || {}, semana = semanaDe(this.relogio());
    const sem = e[semana] || { ok: 0, med: 0, falha: 0, ia: 0 };
    if (Object.hasOwn(sem, resultado)) sem[resultado] = Math.min(100000, sem[resultado] + 1);
    e[semana] = sem;
    const mantidas = Object.keys(e).sort().slice(-LIMITES.semanas);
    await this.memoria.definirMeta(K.estat, Object.fromEntries(mantidas.map((s) => [s, e[s]])));
  }

  async falha(frase) {
    const t = limpo(frase, LIMITES.frase), chave = normalizar(t);
    if (chave.length < 3) return;
    const itens = await this._lista(K.falhas), achada = itens.find((i) => normalizar(i.t) === chave);
    if (achada) { achada.n = Math.min(999, (achada.n || 1) + 1); achada.em = isoData(this.relogio()); itens.splice(itens.indexOf(achada), 1); itens.push(achada); } else itens.push({ t, n: 1, em: isoData(this.relogio()) });  // a mais recente vai para o fim
    await this.memoria.definirMeta(K.falhas, itens.slice(-LIMITES.falhas));
    await this.memoria.definirMeta(K.ultima, t);
  }

  async ultimaFalha() { return (await this._ler(K.ultima)) || ""; }

  async escolha(frase, id) {
    const t = limpo(frase, LIMITES.frase), alvo = limpo(id, 80);
    if (normalizar(t).length < 3 || !alvo) return;
    const itens = (await this._lista(K.escolhas)).filter((i) => normalizar(i.t) !== normalizar(t));
    itens.push({ t, id: alvo, em: isoData(this.relogio()) });
    await this.memoria.definirMeta(K.escolhas, itens.slice(-LIMITES.escolhas));
    const falhas = (await this._lista(K.falhas)).filter((i) => normalizar(i.t) !== normalizar(t));  // o que foi esclarecido deixa de ser "não entendido"
    await this.memoria.definirMeta(K.falhas, falhas);
  }

  // Frase igual (ou com 1 letra trocada, em frases longas) a uma que a pessoa já esclareceu antes.
  async escolhaPara(frase) {
    const chave = normalizar(frase);
    if (chave.length < 3) return null;
    const achada = (await this._lista(K.escolhas)).find((i) => { const c = normalizar(i.t); return c === chave || (c.length >= 10 && distancia(c, chave) <= 1); });
    return achada ? achada.id : null;
  }

  async apelidos() { return (await this._lista(K.apelidos)).filter((a) => typeof a.de === "string" && typeof a.para === "string"); }

  async apelidoPara(frase) {
    const chave = normalizar(frase);
    if (chave.length < 3) return null;
    const a = (await this.apelidos()).find((x) => { const c = normalizar(x.de); return c === chave || (c.length >= 10 && jaccard(trigramas(c), trigramas(chave)) >= 0.85); });
    return a ? a.para : null;
  }

  // Valida e grava um atalho APROVADO pelo usuário. `valido(para)` diz se a frase de destino leva a um comando de leitura ou a um assunto do app.
  async gravarApelido({ de, para }, valido) {
    de = limpo(de, LIMITES.apelido); para = limpo(para, LIMITES.alvo);
    if (normalizar(de).length < 3 || normalizar(para).length < 3) throw new Error("frase curta demais");
    if (normalizar(de) === normalizar(para)) throw new Error("as duas frases são iguais");
    if (!(await valido(para))) throw new Error("só posso ligar a um comando de leitura que eu já conheço");
    const itens = (await this.apelidos()).filter((a) => normalizar(a.de) !== normalizar(de));
    if (itens.length >= LIMITES.apelidos) throw new Error(`limite de ${LIMITES.apelidos} atalhos; apague alguns antes`);
    itens.push({ de, para, em: isoData(this.relogio()) });
    await this.memoria.definirMeta(K.apelidos, itens);
    return { de, para };
  }

  async apagarTudo() { for (const k of CHAVES_EVOLUCAO) await this.memoria.definirMeta(k, null); }

  async resumo() {
    const [estat, falhas, escolhas, apelidos] = await Promise.all([this._ler(K.estat), this._lista(K.falhas), this._lista(K.escolhas), this.apelidos()]);
    return { estat: estat || {}, falhas, escolhas, apelidos };
  }

  static taxa(sem) {
    const total = (sem?.ok || 0) + (sem?.med || 0) + (sem?.falha || 0) + (sem?.ia || 0);
    return { total, pct: total ? Math.round((100 * ((sem.ok || 0) + (sem.med || 0))) / total) : null };
  }

  // Texto de "como estou evoluindo": semana atual contra a anterior, o que mais falhou e o que aprendi.
  async relatorio() {
    const { estat, falhas, escolhas, apelidos } = await this.resumo();
    const agora = this.relogio(), atual = semanaDe(agora), antes = semanaDe(new Date(+agora - 7 * 86400000));
    const a = Aprendizado.taxa(estat[atual]), p = Aprendizado.taxa(estat[antes]);
    const linhas = ["**Como estou evoluindo** (só no seu celular, nada sai daqui)"];
    if (!a.total && !p.total) linhas.push("Ainda não tenho conversas suficientes para medir. Converse comigo e eu volto a mostrar.");
    else {
      if (a.total) linhas.push(`- **Esta semana:** entendi ${a.pct}% dos ${a.total} pedidos (${estat[atual].falha || 0} sem entender, ${estat[atual].ia || 0} passados para a IA).`);
      if (p.total) linhas.push(`- **Semana passada:** ${p.pct}% de ${p.total} pedidos.${a.total && p.total ? (a.pct > p.pct ? " Melhorei." : a.pct < p.pct ? " Caí um pouco: me ensine." : " Igual.") : ""}`);
    }
    const piores = [...falhas].sort((x, y) => (y.n || 1) - (x.n || 1)).slice(0, 3);
    if (piores.length) linhas.push("- **O que mais falhou:** " + piores.map((f) => `“${f.t}”${f.n > 1 ? ` (${f.n}x)` : ""}`).join("; ") + '. Diga "isso significa ..." logo depois para eu aprender.');
    if (escolhas.length || apelidos.length) linhas.push(`- **O que aprendi com você:** ${escolhas.length} esclarecimento(s) e ${apelidos.length} atalho(s)` + (apelidos.length ? ": " + apelidos.slice(-3).map((x) => `“${x.de}” → “${x.para}”`).join("; ") : "") + ".");
    else linhas.push('- **O que aprendi com você:** nada ainda. Ensine: "quando eu disser bom dia chefe, mostre minha agenda".');
    return linhas.join("\n");
  }

  // Aviso ao abrir o app: no máximo uma vez por semana, e só se houve conversa na semana passada.
  async avisoSemanal() {
    const agora = this.relogio(), semana = semanaDe(agora);
    if ((await this._ler(K.relatorio)) === semana) return null;
    const antes = semanaDe(new Date(+agora - 7 * 86400000)), estat = (await this._ler(K.estat)) || {};
    if (Aprendizado.taxa(estat[antes]).total < 5 && Aprendizado.taxa(estat[semana]).total < 5) return null;
    await this.memoria.definirMeta(K.relatorio, semana);
    return await this.relatorio() + `\n_(${dataPorExtenso(agora)})_`;
  }
}
