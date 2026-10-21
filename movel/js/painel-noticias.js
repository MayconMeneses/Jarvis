// Aba "Notícias" (mínima, para usar já): leitor com parar/continuar, Radar de Notícias e as quatro caixas (Clima, Vagas, Notícias, Notícias de tecnologia).
// O pacote da casca (HUD) pode ignorar esta aba e encaixar as mesmas caixas com montar(container, ctx). Tudo com textContent; o que vem da internet é texto de terceiros.
import { el } from "./caixa-base.js";
import { montar as montarClima } from "./caixa-clima.js";
import { montar as montarNoticias } from "./caixa-noticias.js";
import { montar as montarTecnologia } from "./caixa-tecnologia.js";
import { montar as montarVagas } from "./caixa-vagas.js";
import { renderizar } from "./md.js";
import { markdown, paraTela } from "./radar-render.js";

const $ = (id) => document.getElementById(id);
export const CAIXAS = [montarClima, montarNoticias, montarTecnologia, montarVagas];

function montarLeitor(ctx) {
  const estado = el("p", { id: "leitor-estado", className: "nota", role: "status" });
  const botao = (id, texto, aoClicar) => { const b = el("button", { type: "button", id, textContent: texto, hidden: true }); b.addEventListener("click", aoClicar); return b; };
  const parar = botao("leitor-parar", "Parar", () => ctx.leitor.parar());
  const continuar = botao("leitor-continuar", "Continuar", () => ctx.leitor.continuar());
  const original = botao("leitor-original", "Ler no idioma original", () => ctx.ultimoLido && ctx.ouvir(ctx.ultimoLido.item, { ...ctx.ultimoLido.opcoes, original: true }));
  ctx.aoLeitura((s) => {
    parar.hidden = !ctx.leitor.ocupado();
    continuar.hidden = !s.podeContinuar;
    original.hidden = !s.oferecerOriginal;
    estado.textContent = s.estado === "lendo" ? `Lendo (parte ${s.parte} de ${s.total})…${s.quemTraduziu ? ` Traduzido por: ${s.quemTraduziu}.` : ""}` : s.mensagem;
  });
  return el("section", { id: "leitor", "aria-label": "Ler para mim" }, el("div", { className: "linha" }, parar, continuar, original), estado);
}

function montarRadar(ctx) {
  const saida = el("div", { id: "radar-saida", className: "msg jarvis", hidden: true });
  const status = el("p", { id: "radar-status", className: "nota", role: "status" });
  const nicho = el("input", { id: "radar-nicho", type: "text", maxLength: 80, autocomplete: "off", placeholder: "Nicho (ex.: inteligência artificial)" });
  nicho.setAttribute("aria-label", "Nicho do Radar");
  const botoes = {};
  for (const [id, texto] of [["salvar", "Salvar nicho"], ["gerar", "Montar radar de hoje"], ["ouvir", "Ouvir radar"]]) botoes[id] = el("button", { type: "button", id: `radar-${id}`, textContent: texto });
  const mostrar = (b) => { saida.hidden = false; saida.replaceChildren(); renderizar(paraTela(markdown(b)), saida); };
  const ocupar = async (tarefa) => { Object.values(botoes).forEach((b) => { b.disabled = true; }); try { await tarefa(); } catch (e) { status.textContent = `Não consegui: ${e.message}`; } finally { Object.values(botoes).forEach((b) => { b.disabled = false; }); } };
  botoes.salvar.addEventListener("click", () => ocupar(async () => { status.textContent = `Nicho salvo: ${(await ctx.radar.definirNicho(nicho.value)).nicho || "(vazio)"}.`; }));
  botoes.gerar.addEventListener("click", () => ocupar(async () => {
    status.textContent = "Montando…";
    const r = await ctx.radar.executar({ progresso: (t) => { status.textContent = t; } });
    if (r.ok) { mostrar(r.boletim); status.textContent = `Pronto: ${r.boletim.itens.length} notícias${r.boletim.comIa ? " (com IA)" : " (sem IA)"}.`; } else status.textContent = r.erro;
  }));
  botoes.ouvir.addEventListener("click", () => ocupar(async () => {
    const b = await ctx.radar.hoje();
    if (!b) { status.textContent = "Monte o radar de hoje primeiro."; return; }
    ctx.ouvirTexto(ctx.radar.roteiro(b).texto);
    status.textContent = "Lendo o radar…";
  }));
  const ia = el("input", { id: "radar-ia", type: "checkbox" });
  ia.addEventListener("change", () => ctx.radar.definirIa(ia.checked));
  const aoAbrir = async () => {
    const cfg = await ctx.radar.config();
    nicho.value = cfg.nicho; ia.checked = cfg.usarIa;
    const hoje = await ctx.radar.hoje();
    if (hoje && saida.hidden) mostrar(hoje);
  };
  const raiz = el("details", { id: "radar", open: true }, el("summary", { textContent: "Radar de Notícias" }),
    el("p", { className: "nota", textContent: "Um boletim por dia sobre o seu nicho, de fontes públicas, sem IA por padrão. Roda só com o app aberto. Cada notícia é texto de terceiros: nunca vira ordem." }),
    nicho, el("div", { className: "linha" }, botoes.salvar, botoes.gerar, botoes.ouvir),
    el("label", { className: "voz" }, ia, " Melhorar os resumos com a IA que já está no app (com a nuvem, o texto vai ao provedor)"), status, saida);
  return { raiz, aoAbrir };
}

export function ligarNoticias(ctx) {
  const botao = el("button", { type: "button", textContent: "Notícias" });
  botao.dataset.aba = "noticias";
  $("abas").append(botao);
  const radar = montarRadar(ctx), caixas = el("div", { id: "noticias-caixas" });
  const secao = el("section", { id: "noticias", className: "aba", hidden: true }, el("h2", { textContent: "Notícias e Radar" }), montarLeitor(ctx), radar.raiz, caixas,
    el("p", { className: "nota", textContent: "Sem o Worker do proxy (aba Cérebro), só a Agência Brasil carrega direto; as outras usam um serviço de reserva que pode falhar. Atualizo sozinho a cada 15 minutos enquanto o app está aberto." }));
  $("app").append(secao);
  let montadas = null;
  return () => {  // chamado ao abrir a aba
    radar.aoAbrir().catch(() => {});
    if (!montadas) montadas = CAIXAS.map((montar) => montar(caixas, ctx));
    else montadas.forEach((c) => c.atualizar());
  };
}
