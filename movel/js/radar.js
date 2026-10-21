// Radar de Notícias no celular: coleta -> filtro -> dedup -> pontuação -> curadoria -> resumo (sem IA; IA opcional) -> boletim -> memória.
// Mesma lógica do PC (jarvis/radar/executar.py). Falha de uma fonte não derruba o resto; sem nenhuma fonte avisa em vez de gerar boletim vazio.
// Roda só com o app aberto (o iPhone não deixa nada rodar com ele fechado); o boletim fica na memória como a nota Radar/AAAA-MM-DD.
import { carregarFeed } from "./noticias-fontes.js";
import { BLOQUEIOS_PADRAO, escolher, filtrar, novoItem } from "./radar-curadoria.js";
import { agrupar, idDoArtigo } from "./radar-dedup.js";
import { Historico } from "./radar-historico.js";
import { carregarCatalogo, palavrasChave, sugerir } from "./radar-fontes.js";
import { melhorar } from "./radar-ia.js";
import { pontuar } from "./radar-pontuar.js";
import { markdown, novoBoletim } from "./radar-render.js";
import { pareceParede, resumir } from "./radar-resumo.js";
import { montar } from "./radar-roteiro.js";
import { limparTerceiros } from "./radar-sanear.js";
import { isoData } from "./util.js";

export const JANELA_HORAS = 24;
export const LER_ARTIGOS = 3;  // quantos dos melhores itens têm a página lida (só com o Worker); os outros ficam só no RSS
export const SEM_NICHO = 'Defina o nicho do Radar primeiro, por exemplo: "radar nicho inteligência artificial" ou "radar nicho tecnologia".';

export class Radar {
  // proxy: Proxy do rede-proxy.js (ou null). ia(mensagens) -> texto, ou null. catalogo() -> lista de fontes.
  constructor({ memoria, buscar, proxy = null, ia = null, catalogo = null, agora = () => new Date() }) {
    Object.assign(this, { memoria, buscar, proxy, ia, agora, _hist: null });
    this.catalogo = catalogo || (() => (this._cat ||= carregarCatalogo(buscar)));
  }

  async historico() { return (this._hist ||= await new Historico(this.memoria, () => this.agora().getTime() / 1000).carregar()); }
  async config() { return (await this.historico()).config(); }
  async definirNicho(nicho) { return (await this.historico()).definirConfig({ nicho: String(nicho).replace(/\s+/g, " ").trim().slice(0, 80) }); }
  async definirIa(ligada) { return (await this.historico()).definirConfig({ usarIa: Boolean(ligada) }); }
  dia() { return isoData(this.agora()); }

  async hoje() {
    const guardado = await this.memoria.meta("radar:boletim");
    return guardado?.dia === this.dia() && guardado.boletim ? guardado.boletim : null;
  }

  roteiro(boletim, maxPalavras = 800) { return montar(boletim, maxPalavras, this.agora()); }

  async _lerPaginas(escolhidos, avisos) {
    const lendo = this.proxy && await this.proxy.temRota("ler");
    if (!lendo) return avisos.push("sem o Worker não leio as páginas: resumos só do RSS");
    await Promise.all(escolhidos.slice(0, LER_ARTIGOS).map(async (item) => {
      let texto = "", parede = false;
      try {
        texto = limparTerceiros((await this.proxy.ler(item.artigo.link)).texto, 4000);
        parede = pareceParede(texto, item.artigo.resumo);
      } catch (e) { avisos.push(`${item.artigo.fonte}: não li a página (${e.message}); resumo só do RSS`); }
      resumir(item, texto, parede);
    }));
  }

  // Roda o Radar uma vez. { ok, boletim, novos, descartes } ou { ok: false, erro, falhas }.
  async executar({ progresso = () => {} } = {}) {
    const hist = await this.historico(), cfg = await hist.config();
    if (!cfg.nicho.trim()) return { ok: false, erro: SEM_NICHO, falhas: [] };
    const fontes = sugerir(cfg.nicho, await this.catalogo());
    if (!fontes.length) return { ok: false, erro: "O catálogo de fontes está vazio.", falhas: [] };
    progresso(`Lendo ${fontes.length} fontes…`);
    const artigos = [], falhas = [];
    let funcionaram = 0;
    await Promise.all(fontes.map(async (f) => {
      try { artigos.push(...(await carregarFeed(f, { buscar: this.buscar, proxy: this.proxy })).artigos); funcionaram++; } catch (e) { falhas.push(`${f.nome}: ${e.message}`); }
    }));
    const dia = this.dia(), agoraS = this.agora().getTime() / 1000;
    if (!funcionaram) {
      hist.registrarExecucao(dia, 0, 0, 0, falhas, "BLOCKED");
      await hist.salvar();
      const semWorker = falhas.every((f) => f.includes("sem Worker"));
      return { ok: false, falhas, erro: semWorker ? "Sem o Worker do proxy (aba Cérebro) só a Agência Brasil carrega, e ela não é do seu nicho. Cadastre o proxy ou tente com internet."
        : "Nenhuma fonte respondeu: parece que não há internet. Não gerei boletim vazio." };
    }
    const { aceitos, descartes } = filtrar(artigos, BLOQUEIOS_PADRAO, JANELA_HORAS, agoraS);
    const novos = aceitos.filter((a) => !hist.jaVisto(a)), recentes = hist.titulosRecentes(), chaves = palavrasChave(cfg.nicho);
    const itens = agrupar(novos).map(([principal, tambem]) => { const [nota, motivos] = pontuar(principal, chaves, [], JANELA_HORAS, recentes, agoraS); return novoItem(principal, nota, motivos, tambem); });
    const escolhidos = escolher(itens);
    progresso("Resumindo…");
    const avisos = [];
    escolhidos.forEach((item) => resumir(item));
    if (escolhidos.length) await this._lerPaginas(escolhidos, avisos);
    const boletim = Object.assign(novoBoletim(dia, cfg.nicho, escolhidos), { varridos: artigos.length, falhas, avisos });
    if (falhas.length) avisos.push(`${falhas.length} fonte(s) indisponível(is) hoje`);
    if (cfg.usarIa && this.ia && escolhidos.length && !(await melhorar(boletim, this.ia))) avisos.push("a IA não melhorou o texto; fica o resumo sem IA");
    await this.memoria.guardar(`Radar/${dia}`, markdown(boletim), "relatorio", `${escolhidos.length} notícias sobre ${cfg.nicho}`);
    await this.memoria.definirMeta("radar:boletim", { dia, boletim });
    hist.registrar(aceitos, new Set(escolhidos.map((i) => idDoArtigo(i.artigo))));
    hist.registrarExecucao(dia, artigos.length, novos.length, escolhidos.length, falhas, escolhidos.length ? "PASS" : "SEM_ITENS");
    hist.limpar();
    await hist.salvar();
    return { ok: true, boletim, novos: novos.length, descartes };
  }
}
