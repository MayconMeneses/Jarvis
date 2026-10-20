// Aprender sozinha no celular (opt-in, desligado por padrão), como o PC faz: olha o diário de pedidos, acha os assuntos que o usuário
// mais perguntou e que a base não conhece, pesquisa e guarda o resumo como nota "Aprendizado/<assunto>". No máximo 3 por dia.
// Limite honesto: um iPhone não deixa o site rodar em segundo plano; isto só acontece com o app ABERTO e parado (ver agendador.js).
import { buscarTema } from "./aprender.js";
import { fold, isoData } from "./util.js";

export const MAX_POR_DIA = 3, DIAS_DO_DIARIO = 14, MAX_PALAVRAS = 4, MAX_REGISTRO = 60;
const PERGUNTA = /^(?:o que (?:e|sao)|explique|explica|me explica|fale sobre|me fale sobre|conte sobre|descreva|como (?:usar|funciona|instalar|configurar|se usa)|para que serve|quando usar)\s+(?:o |a |os |as |um |uma )?(.+)$/;
const COMUNS = new Set(["isso", "aquilo", "voce", "vc", "tudo", "hoje", "agora", "ajuda", "meu pc", "o pc", "a hora", "hora", "data", "clima"]);

// "o que é Kubernetes?" -> "kubernetes"; frases que não são pergunta sobre um assunto viram null.
export function assuntoDe(frase) {
  const achado = PERGUNTA.exec(fold(frase).trim().replace(/[ ?!.]+$/g, ""));
  if (!achado) return null;
  const tema = achado[1].replace(/\s+(em|no|na|com|para|pra|de|do|da)\s+(python|javascript|js|java|go|c#|node|react).*$/, "").trim();
  const palavras = tema.split(/\s+/);
  return palavras.length >= 1 && palavras.length <= MAX_PALAVRAS && tema.length >= 3 && !COMUNS.has(tema) ? tema : null;
}

export class Autonomo {
  constructor({ memoria, saber, buscar, brave = null, relogio = () => new Date() }) { Object.assign(this, { memoria, saber, buscar, brave, relogio }); }

  async ligado() { return (await this.memoria.meta("autonomo:ligado")) === true; }
  definirLigado(sim) { return this.memoria.definirMeta("autonomo:ligado", Boolean(sim)); }

  async pedidosRecentes() {
    const pedidos = [], hoje = this.relogio();
    for (let i = 0; i < DIAS_DO_DIARIO; i++) {
      const dia = new Date(hoje.getFullYear(), hoje.getMonth(), hoje.getDate() - i);
      const corpo = (await this.memoria.ler(`Diário/${isoData(dia)}`))?.corpo || "";
      for (const linha of corpo.split("\n")) { const m = /Pedido: (.+)$/.exec(linha); if (m) pedidos.push(m[1].trim()); }
    }
    return pedidos;
  }

  async registro() { return (await this.memoria.meta("autonomo:registro")) || []; }

  // Assuntos que o usuário perguntou, a base não conhece, e que ainda não foram estudados (nem tentados), do mais perguntado ao menos.
  async candidatos() {
    const contagem = new Map(), tentados = new Set((await this.registro()).map((r) => fold(r.assunto)));
    for (const frase of await this.pedidosRecentes()) {
      const tema = assuntoDe(frase);
      if (!tema || tentados.has(tema) || this.saber.explicar(tema, "python")) continue;
      if (await this.memoria.ler(`Aprendizado/${tema}`)) continue;
      contagem.set(tema, (contagem.get(tema) || 0) + 1);
    }
    return [...contagem].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([assunto, mencoes]) => ({ assunto, mencoes }));
  }

  async feitosHoje() {
    const d = await this.memoria.meta("autonomo:dia");
    return d && d.data === isoData(this.relogio()) ? d.n : 0;
  }

  // Estuda UM assunto (o mais perguntado). Devolve o que fez ou null (desligada, limite do dia, nada a estudar). Nunca lança.
  async ciclo() {
    if (!(await this.ligado()) || (await this.feitosHoje()) >= MAX_POR_DIA) return null;
    const alvo = (await this.candidatos())[0];
    if (!alvo) return null;
    const entrada = { assunto: alvo.assunto, quando: this.relogio().toISOString(), mencoes: alvo.mencoes, ok: false, origem: "", titulo: "" };
    try {
      const achado = await buscarTema(alvo.assunto, this.buscar, this.brave);
      if (achado) {
        const corpo = `${achado.resumo}\n\nFonte: ${achado.fonte}\n\n_Aprendido sozinha da internet; não verificado. Revise antes de confiar._`;
        await this.memoria.guardar(`Aprendizado/${alvo.assunto}`, corpo, "aprendizado", achado.titulo);
        Object.assign(entrada, { ok: true, origem: achado.origem, titulo: achado.titulo });
      }
    } catch (e) { entrada.erro = String(e.message || e).slice(0, 120); }
    await this.memoria.definirMeta("autonomo:registro", [entrada, ...(await this.registro())].slice(0, MAX_REGISTRO));
    await this.memoria.definirMeta("autonomo:dia", { data: isoData(this.relogio()), n: (await this.feitosHoje()) + 1 });
    if (entrada.ok) await this.memoria.diario(`Aprendi sozinha: ${alvo.assunto}`);
    return entrada;
  }

  async relatorio() {
    const feitos = (await this.registro()).filter((r) => r.ok);
    const estado = (await this.ligado()) ? "ligada" : 'desligada (ligue em Cérebro → "Aprender sozinha")';
    if (!feitos.length) return `Ainda não aprendi nada sozinha. Aprender sozinha: ${estado}. Só funciona com o app aberto e parado por uns 10 minutos, até ${MAX_POR_DIA} assuntos por dia.`;
    return `**O que aprendi sozinha** (aprender sozinha: ${estado}):\n` + feitos.slice(0, 10).map((r) => `- **${r.assunto}** (${isoData(new Date(r.quando))}, ${r.origem}) — nota "Aprendizado/${r.assunto}"`).join("\n")
      + "\n\nTudo vem da internet e não foi verificado: veja e apague na aba Memória.";
  }
}
