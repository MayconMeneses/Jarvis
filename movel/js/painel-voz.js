// Cérebro > Voz: voz de saída (aparelho ou Gemini), escolha da voz do iOS com teste, e a escuta por "Jarvis". Monta o próprio bloco (sem mexer no index.html).
import { VOZES_GEMINI } from "./voz-gemini.js";
import { listarVozesPt, pontuar } from "./voz-escolha.js";

export const AVISO_GEMINI = "A voz do Gemini manda o TEXTO das respostas que a Jarvis vai falar para o Google (usando a sua chave Gemini) para virar áudio. "
  + "O áudio do seu microfone NÃO é enviado por esta opção. Se não quiser que esses textos saiam do aparelho, fique com a voz do aparelho. Ligar?";

const rotulo = (v) => `${v.name}${/enhanced|premium|aprimorad/i.test(`${v.name} ${v.voiceURI}`) ? " (aprimorada)" : ""} — ${v.lang}`;

// deps: { saida, escuta, memoria, nuvem, avisar, doc?, confirmar? }
export async function montarPainelVoz(pai, { saida, escuta, memoria, nuvem, avisar = () => {}, doc = globalThis.document, confirmar = (t) => globalThis.confirm(t) }) {
  const el = (tag, props = {}, ...filhos) => { const e = doc.createElement(tag); Object.assign(e, props); e.append(...filhos); return e; };
  const campo = (texto, controle) => el("label", {}, texto, controle);
  const sel = (opcoes, valor) => { const s = el("select"); s.append(...opcoes.map(([v, t]) => el("option", { value: v, textContent: t }))); s.value = valor; return s; };
  const caixa = (marcado) => el("input", { type: "checkbox", checked: marcado });

  const [provedor, vozURI, vozG, foco, conversa] = await Promise.all(["voz_provedor", "voz_navegador_voz", "voz_gemini_voz", "voz_foco_auto", "voz_escuta_conversa"].map((k) => memoria.meta(k)));
  const temChave = Boolean(await nuvem.chaveGemini().catch(() => null));
  const usaGemini = provedor === "gemini" && temChave;
  saida.configurar({ provedor: usaGemini ? "gemini" : "navegador", vozURI: vozURI || null, vozGemini: VOZES_GEMINI.includes(vozG) ? vozG : "Kore" });

  const status = el("p", { className: "nota", role: "status" });
  const vozes = () => listarVozesPt(saida.sintese?.getVoices?.() || []);
  const selProvedor = sel([["navegador", "Voz do aparelho (padrão, sem enviar nada)"], ["gemini", "Voz do Gemini (envia o texto ao Google)"]], usaGemini ? "gemini" : "navegador");
  const selAparelho = sel([["", "Automática (a melhor pt-BR instalada)"]], vozURI || "");
  const selGemini = sel(VOZES_GEMINI.map((n) => [n, n]), saida.config.vozGemini);
  const chkFoco = caixa(foco !== false), chkConversa = caixa(conversa === true);

  const desenharVozes = () => {
    const lista = vozes();
    selAparelho.replaceChildren(el("option", { value: "", textContent: "Automática (a melhor pt-BR instalada)" }), ...lista.map((v) => el("option", { value: v.voiceURI, textContent: rotulo(v) })));
    selAparelho.value = lista.some((v) => v.voiceURI === saida.config.vozURI) ? saida.config.vozURI : "";
    const melhor = lista[0];
    status.textContent = !lista.length ? "Nenhuma voz em português encontrada. Instale em Ajustes > Acessibilidade > Conteúdo falado > Vozes > Português (Brasil)."
      : pontuar(melhor) >= 145 ? `Voz automática: ${melhor.name}.` : `Voz automática: ${melhor.name}. Para uma voz melhor, baixe a versão Aprimorada em Ajustes > Acessibilidade > Conteúdo falado > Vozes > Português (Brasil).`;
  };
  saida.sintese?.addEventListener?.("voiceschanged", desenharVozes);  // o iPhone entrega a lista depois de alguns instantes

  selProvedor.addEventListener("change", async () => {
    if (selProvedor.value === "gemini") {
      if (!(await nuvem.chaveGemini().catch(() => null))) { selProvedor.value = "navegador"; status.textContent = "Cadastre primeiro a sua chave do Gemini em Cérebro > Nuvem."; return; }
      if (!confirmar(AVISO_GEMINI)) { selProvedor.value = "navegador"; return; }
    }
    saida.configurar({ provedor: selProvedor.value });
    await memoria.definirMeta("voz_provedor", selProvedor.value);
    status.textContent = selProvedor.value === "gemini" ? "Voz do Gemini ligada. Se falhar, uso a voz do aparelho." : "Voz do aparelho ligada.";
  });
  selAparelho.addEventListener("change", async () => { saida.configurar({ vozURI: selAparelho.value || null }); await memoria.definirMeta("voz_navegador_voz", selAparelho.value || ""); });
  selGemini.addEventListener("change", async () => { saida.configurar({ vozGemini: selGemini.value }); await memoria.definirMeta("voz_gemini_voz", selGemini.value); });
  chkFoco.addEventListener("change", async () => { escuta.configurar({ focoAuto: chkFoco.checked }); await memoria.definirMeta("voz_foco_auto", chkFoco.checked); });
  chkConversa.addEventListener("change", async () => {
    await memoria.definirMeta("voz_escuta_conversa", chkConversa.checked);
    if (chkConversa.checked) { saida.destravar(); if (!escuta.iniciar()) status.textContent = "Este navegador não tem reconhecimento de fala."; } else escuta.parar();
  });
  const testar = el("button", { type: "button", textContent: "Testar a voz" });
  testar.addEventListener("click", () => { saida.destravar(); saida.testar(); });
  const parar = el("button", { type: "button", textContent: "Parar" });
  parar.addEventListener("click", () => saida.parar());
  const nota = el("p", { className: "nota", textContent: "Escuta por “Jarvis”: o reconhecimento de fala é o do navegador (no iPhone, a Apple processa a fala). A Jarvis não grava nem guarda áudio. "
    + "Só funciona com o app aberto e a tela ligada: com a tela bloqueada ou o app fechado o iPhone encerra o microfone. O ponto laranja do iOS e a barra “Microfone ligado” mostram quando está ouvindo." });

  const bloco = el("details", { className: "painel-extra", id: "painel-voz" }, el("summary", { textContent: "Voz" }),
    campo("Voz de saída", selProvedor), campo("Voz do aparelho", selAparelho), campo("Voz do Gemini", selGemini),
    el("div", { className: "linha" }, testar, parar), status,
    el("label", {}, chkFoco, " Ouvir “Jarvis” no modo foco (liga o microfone ao entrar)"),
    el("label", {}, chkConversa, " Ouvir “Jarvis” também na conversa (microfone aberto enquanto o app estiver na tela)"), nota);
  pai.append(bloco);
  escuta.configurar({ focoAuto: foco !== false });
  desenharVozes();
  return { bloco, desenharVozes, selProvedor, selAparelho, selGemini, chkFoco, chkConversa, status, ligarConversa: conversa === true };
}
