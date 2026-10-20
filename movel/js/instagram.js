// Analista de Instagram no celular: guarda tudo SÓ neste aparelho (meta "instagram", fora das notas e do contexto da IA), calcula sozinho
// e monta o relatório. Só métricas públicas e ~200 caracteres da legenda. Não acessa o Instagram: os dados são colados pelo usuário.
import { chavePost, epoch } from "./instagram-base.js";
import { aplicar } from "./instagram-entrevista.js";
import { ler } from "./instagram-importar.js";
import { analisar } from "./instagram-metricas.js";
import { comparar, montar, textoComparacao } from "./instagram-relatorio.js";
import { semanaIso } from "./util.js";

const CHAVE = "instagram", MAX_RODADAS = 12;
const vazio = () => ({ analise: {}, seguidores: {}, rodadas: [], lembrete: false });
const mesmaSemana = (a, b) => semanaIso(a).join("-") === semanaIso(b).join("-");

export class Instagram {
  constructor(memoria, relogio = () => new Date()) { this.memoria = memoria; this.relogio = relogio; }

  async estado() { return { ...vazio(), ...((await this.memoria.meta(CHAVE)) || {}) }; }
  salvar(estado) { return this.memoria.definirMeta(CHAVE, estado); }

  async configurar(texto) {
    const e = await this.estado(), [perfil, faltam, avisos] = aplicar(texto, e.analise);
    e.analise = perfil;
    for (const [arroba, seg] of Object.entries(perfil.concorrentes || {})) if (seg != null || !(arroba in e.seguidores)) e.seguidores[arroba] = seg ?? e.seguidores[arroba] ?? null;
    await this.salvar(e);
    const linhas = ["Perfil da análise de Instagram atualizado.", ...avisos.map((a) => `Aviso: ${a}`)];
    if (faltam.length) linhas.push("Ainda preciso de (responda com \"configurar instagram\" e uma linha por campo):", ...faltam.map((p) => `- ${p}`));
    else linhas.push("Tudo certo. Agora cole os posts: \"importar posts\" e, na linha seguinte, a tabela (perfil, link, data, formato, legenda, likes, comentarios, views...).");
    return linhas.join("\n");
  }

  async importar(texto, perfilPadrao = "", nova = false) {
    const lido = ler(texto, perfilPadrao);
    if (!lido.posts.length) return "Não importei nenhum post. " + lido.avisos.slice(0, 3).join("; ");
    const e = await this.estado(), agora = this.relogio(), ultima = e.rodadas.at(-1);
    let rodada = ultima && !nova && mesmaSemana(new Date(ultima.criada), agora) ? ultima : null;
    if (!rodada) { rodada = { id: (ultima?.id ?? 0) + 1, criada: agora.toISOString(), posts: {} }; e.rodadas.push(rodada); e.rodadas = e.rodadas.slice(-MAX_RODADAS); }
    let novos = 0, atualizados = 0;
    for (const p of lido.posts) { const k = chavePost(p); if (k in rodada.posts) atualizados++; else novos++; rodada.posts[k] = p; }
    for (const [arroba, seg] of Object.entries(lido.seguidores)) e.seguidores[arroba] = seg;
    for (const p of lido.posts) if (!(p.perfil in e.seguidores)) e.seguidores[p.perfil] = null;
    await this.salvar(e);
    const linhas = [`Importei ${novos} posts novos e atualizei ${atualizados} na rodada ${rodada.id} (de ${new Set(lido.posts.map((p) => p.perfil)).size} perfis).`,
      ...lido.avisos.slice(0, 6).map((a) => `- ${a}`)];
    if (lido.avisos.length > 6) linhas.push(`- ... e mais ${lido.avisos.length - 6} avisos`);
    return [...linhas, "Diga \"relatório de instagram\" para ver a análise."].join("\n");
  }

  resultado(e, rodada) {
    const agora = epoch(this.relogio().toISOString().slice(0, 19));
    return analisar(Object.values(rodada.posts), e.seguidores, e.analise.pesos, agora, e.analise.proprio || "");
  }

  async relatorio() {
    const e = await this.estado(), r = e.rodadas.at(-1);
    if (!r) return "Ainda não tenho posts. Diga \"analisar instagram\" para configurar e \"importar posts\" para colar os dados.";
    return montar(this.resultado(e, r), e.analise.nicho || "", String(r.id));
  }

  async comparar() {
    const e = await this.estado();
    if (e.rodadas.length < 2) return "Preciso de pelo menos duas rodadas com posts para comparar (cole os dados de novo na próxima semana, com \"importar posts\").";
    const [a, b] = e.rodadas.slice(-2);
    return textoComparacao(comparar(this.resultado(e, a), this.resultado(e, b)), String(a.id), String(b.id));
  }

  async analisarComando() {
    const e = await this.estado();
    if (!e.analise.nicho) return (await this.configurar("")) + "\n\nExemplo: configurar instagram nicho: confeitaria; meu perfil: @doces; concorrentes: @a (12 mil), @b (8,5 mil)";
    return this.relatorio();
  }

  async apagar(alvo) {
    const e = await this.estado();
    if (alvo === "tudo") { await this.salvar({ ...vazio(), lembrete: e.lembrete }); return "Todos os dados de Instagram foram apagados deste aparelho."; }
    let n = 0;
    for (const r of e.rodadas) for (const [k, p] of Object.entries(r.posts)) if (p.perfil === alvo) { delete r.posts[k]; n++; }
    delete e.seguidores[alvo];
    await this.salvar(e);
    return `${n} posts de ${alvo} apagados.`;
  }

  async definirLembrete(ligado) { const e = await this.estado(); e.lembrete = Boolean(ligado); await this.salvar(e); }

  // Aviso ao abrir o app, segunda-feira, uma vez por semana, só se houver rodada (o iPhone não acorda o app sozinho). Quem chama também FALA.
  async aviso(agora = this.relogio()) {
    const e = await this.estado();
    if (!e.lembrete || agora.getDay() !== 1 || agora.getHours() < 9 || agora.getHours() >= 20 || !e.rodadas.length) return null;
    const chave = "aviso:instagram:" + semanaIso(agora).join("-");
    if (await this.memoria.meta(chave)) return null;
    await this.memoria.definirMeta(chave, true);
    const dias = Math.round((agora - new Date(e.rodadas.at(-1).criada)) / 86400000);
    return { texto: `📊 Instagram: faz ${dias} dias da última rodada. Exporte os 12 últimos posts de cada @ e cole aqui, ou diga "importar posts".`,
      fala: `Segunda-feira: hora de atualizar a análise do Instagram. Faz ${dias} dias da última rodada.` };
  }
}
