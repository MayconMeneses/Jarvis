// Início (HUD central do celular): orbe + cartão de briefing em cima; caixas embaixo (rolagem), reordenáveis. Junta módulos que já existem:
// caixas de notícias/clima/vagas (montar(container, ctx)), cartões do PC pareado (painel-pc-geral.js) e as caixas locais (caixas-celular.js).
import { montar as montarClima } from "./caixa-clima.js";
import { montar as montarNoticias } from "./caixa-noticias.js";
import { montar as montarTecnologia } from "./caixa-tecnologia.js";
import { montar as montarVagas } from "./caixa-vagas.js";
import { montarAgentes, montarUso } from "./caixas-celular.js";
import { criarGrade } from "./hud-grade.js";
import { montarCartao } from "./hud-cartao.js";
import { lembretesDeHoje } from "./hud-briefing.js";
import { montar as montarPainelPc } from "./painel-pc-geral.js";
import { isoData } from "./util.js";

const $ = (id) => document.getElementById(id);
const no = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };
const hora = () => new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });

export function ligarHud({ memoria, ctx, pc, uso, agentes, autonomo, avaliador, cerebro, avisar = () => {} }) {
  const secao = $("hud"), aviso = $("hud-aviso"), relogio = $("hora");
  const grade = criarGrade($("hud-caixas"), { memoria, anunciar: (t) => { aviso.textContent = t; } });
  const visivel = () => !secao.hidden && document.visibilityState === "visible";
  const caixas = [];

  // Caixas da internet e do celular: cada módulo se monta num suporte solto e a caixa vai para a grade.
  const suporte = () => no("div");
  const caixa = (id, titulo, criar) => { const s = suporte(), c = criar(s); caixas.push(c); grade.registrar(id, titulo, c.el); return c; };
  caixa("clima", "Clima", (s) => montarClima(s, ctx));
  caixa("vagas", "Vagas", (s) => montarVagas(s, ctx));
  caixa("noticias", "Últimas notícias", (s) => montarNoticias(s, ctx));
  caixa("tecnologia", "Notícias de tecnologia", (s) => montarTecnologia(s, ctx));
  caixa("uso-ia", "Uso de IA", (s) => montarUso(s, ctx, { uso }));
  caixa("agentes", "Agentes do app", (s) => montarAgentes(s, ctx, { agentes, autonomo, avaliador, cerebro }));

  // Cartões do PC pareado: o painel é montado num suporte e cada cartão vira uma caixa; o que sobra (aviso e botão Atualizar) é a caixa "PC".
  const s = suporte(), painelPc = montarPainelPc(s, { pc });
  const idsPc = painelPc.cartoes.map((m) => m.id);
  for (const m of painelPc.cartoes) { m.cartao.raiz.classList.add("caixa"); grade.registrar(m.id, m.titulo, m.cartao.raiz, { visivel: false }); }
  const caixaPc = no("section", { className: "caixa", id: "caixa-pc" }, no("h3", { textContent: "Seu PC (somente leitura)" }), ...s.childNodes);
  grade.registrar("pc", "Seu PC", caixaPc);

  // Cartão central: agenda local (lembretes) quando não há PC; com o PC pareado vem a agenda e os e-mails dele.
  const cartao = montarCartao($("briefing"), { aoAbrir: (aba) => { const alvo = { agenda: "item-pc-agenda", emails: "item-pc-emails", noticias: "item-noticias" }[aba]; const el = $(alvo); if (el && !el.hidden) el.scrollIntoView?.({ block: "start" }); else $("item-pc")?.scrollIntoView?.({ block: "start" }); } });
  const noticias = () => cartao.definir({ noticias: ctx.noticias.ultima });
  Promise.all(caixas.map((c) => c.pronto)).then(noticias).catch(() => {});
  $("briefing").addEventListener("click", noticias);

  async function lembretes() { try { return lembretesDeHoje(await memoria.listar("Lembretes/"), isoData(new Date())); } catch { return []; } }

  // Atualiza o PC pareado; mostra os cartões só se há PC; alimenta o cartão central com o que acabou de ler.
  async function atualizarPc() {
    const pareado = await pc.pareado();
    idsPc.forEach((id) => grade.definirVisivel(id, pareado));
    const rs = await painelPc.atualizar();
    const de = (id) => { const r = rs[idsPc.indexOf(id)]; return r && r.ok ? r.dados : null; };
    cartao.definir({ agenda: pareado ? de("pc-agenda") : null, emails: pareado ? de("pc-emails") : null, lembretes: await lembretes(), nome: (await memoria.meta("nome")) || "Maycon", hora: new Date().getHours() });
    return rs;
  }

  // Modo Reordenar (subir/descer) e Restaurar layout.
  const botao = $("reordenar");
  botao.addEventListener("click", () => { grade.reordenar(!grade.reordenando); botao.setAttribute("aria-pressed", String(grade.reordenando)); botao.textContent = grade.reordenando ? "Concluir" : "Reordenar"; });
  async function restaurar() { await grade.restaurar(); botao.setAttribute("aria-pressed", "false"); botao.textContent = "Reordenar"; }

  const tique = () => { relogio.textContent = hora(); };
  tique();
  setInterval(() => { if (visivel()) tique(); }, 30000);
  const pronto = grade.carregar().then(() => atualizarPc()).catch(() => {});
  return {
    pronto, restaurar, atualizarPc, visivel, grade, cartao,
    // Chamado quando a aba Início volta a aparecer: caixas só recarregam se passou do prazo (15 min), o PC lê de novo.
    aoAbrir() { tique(); caixas.forEach((c) => c.atualizar()); atualizarPc().catch(() => {}); noticias(); },
    painelPc: { atualizar: atualizarPc },
  };
}
