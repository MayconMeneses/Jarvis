// Jarvis do celular: junta memória, conhecimento, motor de regras e (se ligado) o cérebro de IA do aparelho.
import { avisos } from "./proativo.js";
import { adicionar, atualizar, destravarFala, falar, ligarConversaPorVoz, ligarDitado, pensando, usarOrbe } from "./chat.js";
import { mostrarCartao } from "./cartao-memoria.js";
import { extrair, semProposta } from "./memoria-viva.js";
import { ligarOrbe } from "./orbe-ui.js";
import { ligarAparencia } from "./painel-aparencia.js";
import { Agentes } from "./agentes.js";
import { ligarAgentes } from "./painel-agentes.js";
import { Uso } from "./uso.js";
import { ligarUso } from "./painel-uso.js";
import { Autonomo } from "./autonomo.js";
import { Avaliador } from "./avaliar.js";
import { Cerebro } from "./cerebro.js";
import { Nuvem } from "./nuvem.js";
import { ligarNuvem } from "./painel-nuvem.js";
import { PcPareado } from "./pc-pareado.js";
import { ligarPc } from "./painel-pc.js";
import { Conversa } from "./conversa.js";
import * as contexto from "./contexto.js";
import { ArmazemIndexedDB, ArmazemMemoria, Memoria } from "./memoria.js";
import { Motor } from "./motor.js";
import { ligarAutonomo } from "./painel-autonomo.js";
import { ligarCerebro } from "./painel-cerebro.js";
import { ligarMemoria } from "./painel-memoria.js";
import { Instagram } from "./instagram.js";
import { ligarInstagram } from "./painel-instagram.js";
import { Documentos } from "./documentos.js";
import { montarDocumentos } from "./painel-documentos.js";
import { ligarOficina } from "./painel-oficina.js";
import { ligarCriarComIA } from "./painel-oficina-ia.js";
import { criarContexto } from "./noticias-ctx.js";
import { ligarNoticias } from "./painel-noticias.js";
import { executar as rodarNoSandbox } from "./sandbox.js";
import { Saber } from "./saber.js";
import { ligarNavegacao } from "./navegacao.js";
import { ligarRetomada } from "./rascunho.js";
import { ligarTeclado } from "./teclado.js";
import { ligarAtualizacao } from "./atualizacao.js";
import { erroHumano } from "./erros.js";

const $ = (id) => document.getElementById(id);

async function iniciarMemoria() {
  try {
    const armazem = new ArmazemIndexedDB();
    await armazem.chaves();  // falha cedo em modo privado
    if (navigator.storage?.persist) navigator.storage.persist();  // pede ao iPhone para não apagar a memória
    return new Memoria(armazem);
  } catch (e) {
    adicionar(erroHumano(e), "aviso");
    return new Memoria(new ArmazemMemoria());
  }
}

// Sem o conhecimento (rede caída no primeiro uso, arquivo corrompido) o app abre mesmo assim, só com o motor básico.
async function carregarSaber() {
  try {
    const r = await fetch("dados/saber.json");
    if (!r.ok) throw new Error("HTTP " + r.status);
    return new Saber(await r.json());
  } catch (e) {
    setTimeout(() => adicionar("Não consegui carregar a base de conhecimento (" + erroHumano(e) + ") Abro só com o básico; ao reabrir com internet ela volta.", "aviso"), 0);
    return new Saber({});
  }
}

async function main() {
  const [saber, memoria] = await Promise.all([carregarSaber(), iniciarMemoria()]);  // em paralelo: o JSON de 200 KB não espera o IndexedDB
  await ligarAparencia(memoria);
  const uso = new Uso(memoria), agentes = new Agentes(memoria);
  const contar = (fonte, dados) => uso.registrar(fonte, dados).catch(() => {});  // contadores locais: nunca atrapalham a conversa
  const nuvem = new Nuvem({ armazem: memoria.armazem, aoUsar: contar });
  // A busca do Brave é contada por chamada (o proxy do usuário recebe a chave; aqui só passa a contagem).
  const buscarMedido = (url, opcoes) => { if (String(url).includes("/brave/res/v1/")) contar("brave"); return fetch(url, opcoes); };
  const motor = new Motor({ saber, memoria, buscar: buscarMedido, brave: () => nuvem.brave() });
  const cerebro = new Cerebro({ aoUsar: contar });
  const conversa = new Conversa(memoria);
  const nome = async () => (await memoria.meta("nome")) || "Maycon";

  // A linha [[SAVE:...]] some do texto (exibido, falado, guardado na conversa); vira um cartão que o usuário aprova ou descarta.
  const cartoes = async (propostas, dados) => {
    for (const proposta of propostas) await mostrarCartao({ proposta, memoria, dadosExternos: Boolean(dados), onde: $("mensagens") });
  };

  async function perguntarIA(texto) {
    const dados = (await motor.consultarAntes(texto)) || "";
    const sistema = await contexto.sistema({ saber, memoria, pergunta: texto, nome: await nome(), dados });
    const mensagens = [{ role: "system", content: sistema }, ...conversa.paraPrompt()];  // cabe no contexto do modelo, sempre
    const bolha = adicionar("…", "jarvis", cerebro.modelo);
    pensando(true, "IA pensando…");
    try {
      const resposta = await cerebro.perguntar(mensagens, (parcial) => atualizar(bolha, semProposta(parcial)), (aviso) => atualizar(bolha, aviso));
      agentes.marcar("cerebro", "ok");
      const { texto: limpo, propostas } = extrair(resposta || "");
      atualizar(bolha, limpo || "Não consegui responder.");
      await cartoes(propostas, dados);
      return limpo;
    } catch (e) {
      agentes.marcar("cerebro", "erro");
      atualizar(bolha, `Não consegui responder agora (${e.message}). A conversa continua: pode perguntar de novo.`);
      bolha.classList.add("erro");
      return "";
    } finally { pensando(false); }
  }

  // Nuvem (as chaves do usuário): histórico maior, porque esses modelos aguentam bem mais contexto.
  async function perguntarNuvem(texto) {
    const dados = (await motor.consultarAntes(texto)) || "";
    const sistema = await contexto.sistema({ saber, memoria, pergunta: texto, nome: await nome(), dados });
    const bolha = adicionar("…", "jarvis");
    pensando(true, "consultando a nuvem…");
    try {
      const r = await nuvem.perguntar([{ role: "system", content: sistema }, ...conversa.paraPrompt(9000)], (parcial) => atualizar(bolha, semProposta(parcial)));
      const { texto: limpo, propostas } = extrair(r.texto);
      atualizar(bolha, limpo);
      const nota = document.createElement("small");
      nota.textContent = r.provedor;
      bolha.appendChild(nota);
      await cartoes(propostas, dados);
      return limpo;
    } catch (e) {
      bolha.remove();
      throw e;
    } finally { pensando(false); }
  }

  // Ordem escolhida pelo usuário: aparelho primeiro (padrão, privado) ou nuvem primeiro (mais capaz). Se um falha, tenta o outro.
  async function responderComIA(texto) {
    const nuvemPrimeiro = (await memoria.meta("nuvem_ordem")) === "nuvem";
    const opcoes = [];
    if (cerebro.ligado()) opcoes.push(["aparelho", perguntarIA]);
    if (await nuvem.configurada()) opcoes[nuvemPrimeiro ? "unshift" : "push"](["nuvem", perguntarNuvem]);
    for (const [, tentar] of opcoes) {
      try { const r = await tentar(texto); if (r) return r; } catch (e) { adicionar("Não consegui por esse caminho (" + e.message + ").", "jarvis aviso"); }
    }
    return opcoes.length ? "" : null;
  }

  // A Oficina usa o mesmo cérebro e a mesma ordem da conversa (aparelho ou nuvem), mas sem mexer na conversa nem falar.
  async function conversaOficina(mensagens) {
    const nuvemPrimeiro = (await memoria.meta("nuvem_ordem")) === "nuvem";
    const opcoes = [];
    if (cerebro.ligado()) opcoes.push(() => cerebro.perguntar(mensagens));
    if (await nuvem.configurada()) opcoes[nuvemPrimeiro ? "unshift" : "push"](async () => (await nuvem.perguntar(mensagens, () => {})).texto);
    if (!opcoes.length) throw new Error("ligue o cérebro do aparelho ou cadastre uma chave de nuvem na aba Cérebro");
    let ultimo;
    for (const tentar of opcoes) { try { return await tentar(); } catch (e) { ultimo = e; } }
    throw ultimo;
  }

  // Um turno de conversa: devolve o texto da resposta (a fala fica por conta de quem chamou).
  async function responder(texto) {
    await conversa.adicionar("user", texto);
    await memoria.diario(`Pedido: ${texto.slice(0, 200)}`);
    pensando(true);
    let resposta = "";
    try {
      resposta = await motor.responder(texto);  // regras primeiro: dados exatos, instantâneo, sem gastar bateria
      const comIA = resposta === null && (cerebro.ligado() || await nuvem.configurada());
      if (comIA) { pensando(false); resposta = await responderComIA(texto); }
      if (!comIA || resposta === null) {
        if (resposta === null || resposta === undefined) resposta = await motor.fallback(texto);
        adicionar(resposta, "jarvis");
      }
    } catch (e) {
      adicionar("Algo deu errado: " + e.message + ". A conversa continua: pode perguntar de novo.", "jarvis erro");
    } finally { pensando(false); }
    await conversa.adicionar("assistant", resposta);
    return resposta;
  }

  async function enviar(texto) {
    texto = texto.trim();
    if (!texto) return;
    destravarFala();
    adicionar(texto, "eu");
    $("texto").value = "";
    falar(await responder(texto));
  }

  $("form").addEventListener("submit", (ev) => { ev.preventDefault(); enviar($("texto").value); });
  document.querySelectorAll("#atalhos button").forEach((b) => b.addEventListener("click", () => enviar(b.dataset.texto)));
  usarOrbe(await ligarOrbe(memoria));
  ligarDitado(enviar);
  ligarConversaPorVoz(responder);

  // A leitura em voz alta vem ligada (lembra a escolha): a Jarvis "conversa", não só escreve.
  $("falar").checked = (await memoria.meta("falar")) !== false;
  $("falar").addEventListener("change", () => memoria.definirMeta("falar", $("falar").checked));
  $("nova-conversa").addEventListener("click", async () => {
    await conversa.limpar();
    $("mensagens").replaceChildren();
    adicionar("Conversa nova. A memória (notas e lembranças) continua guardada.", "jarvis aviso");
  });

  // Aprender sozinha e avaliar o cérebro (a avaliação roda o código da IA só no ambiente isolado da Oficina).
  const autonomo = new Autonomo({ memoria, saber, buscar: buscarMedido, brave: () => nuvem.brave() });
  const avaliador = new Avaliador({
    memoria, conversa: conversaOficina, rodar: rodarNoSandbox,
    disponivel: async () => cerebro.ligado() || (await nuvem.configurada()),
    rotulo: () => (cerebro.ligado() ? cerebro.modelo : "nuvem"),
  });
  const instagram = new Instagram(memoria);
  const pc = new PcPareado({ armazem: memoria.armazem });
  Object.assign(motor, { autonomo, avaliador, instagram, pc, uso });
  const noticiasCtx = criarContexto({ memoria, nuvem, ia: conversaOficina, buscar: buscarMedido, avisar: (t) => adicionar(t, "aviso") });  // caixas, Radar e Ler para mim
  motor.noticiasCtx = noticiasCtx;
  ligarAgentes({ agentes, autonomo, avaliador, cerebro });
  ligarUso({ uso, avisar: (t) => adicionar(t, "aviso") });
  const aoAbrirAgenda = ligarPc({ pc, avisar: (t) => adicionar(t, "aviso") });
  const aoAbrirInstagram = ligarInstagram({ instagram, avisar: (t) => adicionar(t, "aviso") });
  const aoAbrirAutonomo = ligarAutonomo({ autonomo, avaliador, agentes, avisar: (t) => adicionar(t, "aviso") });
  aoAbrirAutonomo();
  const aoAbrirMemoria = ligarMemoria(memoria, (t) => adicionar(t, "aviso"));
  const religar = ligarCerebro(cerebro, memoria, (t) => adicionar(t, "aviso"));
  const aoAbrirNuvem = ligarNuvem(nuvem, memoria, (t) => adicionar(t, "aviso"));
  aoAbrirNuvem();
  let modelosProntos = null;
  const oficina = ligarOficina({ memoria, aoRodar: (e) => agentes.marcar("oficina", e), avisar: (t) => adicionar(t, "aviso"), carregarModelos: async () => (modelosProntos ||= await (await fetch("dados/modelos.json")).json()) });
  ligarCriarComIA({ conversa: conversaOficina, oficina, avisar: (t) => adicionar(t, "aviso") });
  motor.documentos = new Documentos({ memoria, conversa: conversaOficina, nuvem, buscar: buscarMedido, brave: () => nuvem.brave() });  // anexos, criar documentos e pesquisa em níveis
  montarDocumentos($("documentos"), { documentos: motor.documentos, avisar: (t) => adicionar(t, "aviso") });
  const aoAbrirNoticias = ligarNoticias(noticiasCtx);
  const abas = [...document.querySelectorAll("#abas button[data-aba]")];
  abas.forEach((b) => b.addEventListener("click", () => {
    abas.forEach((x) => { if (x === b) x.setAttribute("aria-current", "page"); else x.removeAttribute("aria-current"); });
    b.scrollIntoView?.({ inline: "center", block: "nearest" });  // a aba escolhida não fica escondida na rolagem da barra
    document.querySelectorAll(".aba").forEach((a) => { a.hidden = a.id !== b.dataset.aba; });
    if (b.dataset.aba === "memoria") aoAbrirMemoria();
    if (b.dataset.aba === "instagram") aoAbrirInstagram();
    if (b.dataset.aba === "agenda") aoAbrirAgenda();
    if (b.dataset.aba === "noticias") aoAbrirNoticias();
    if (b.dataset.aba === "oficina") oficina.aoAbrir().catch((e) => adicionar("Não consegui abrir a Oficina: " + e.message, "jarvis erro"));
  }));
  ligarNavegacao();
  ligarRetomada({ campo: $("texto"), abas });
  ligarTeclado();

  const anterior = await conversa.carregar();
  if (anterior.length) {  // conversa contínua: ao reabrir (ou se o iPhone recarregar o app), ela continua de onde parou
    adicionar("Continuando de onde paramos:", "jarvis aviso");
    for (const m of anterior.slice(-12)) adicionar(m.content, m.role === "user" ? "eu" : "jarvis");
  } else {
    adicionar("Olá! Eu sou a Jarvis e rodo **só neste celular**: minha memória e meu cérebro ficam aqui. Pode escrever ou tocar em **Conversar por voz**. Diga \"ajuda\" para ver o que sei fazer.", "jarvis");
  }
  for (const aviso of await avisos({ memoria, saber, nome: await nome() })) adicionar(aviso, "jarvis aviso");
  agentes.marcar("proativo", "ok");
  const gasto = await uso.resumo();
  if (gasto.alerta) adicionar(`Atenção: você já usou ${gasto.pct.toFixed(0)}% do orçamento de IA deste mês (painel Uso de IA, na aba Cérebro).`, "jarvis aviso");
  const lembreteInsta = await instagram.aviso();  // segunda-feira: avisa e FALA (voz do navegador), uma vez por semana
  if (lembreteInsta) { adicionar(lembreteInsta.texto, "jarvis aviso"); falar(lembreteInsta.fala, true); }
  religar();
  if ("serviceWorker" in navigator && window.isSecureContext) { ligarAtualizacao(); navigator.serviceWorker.register("sw.js", { updateViaCache: "none" }).catch(() => {}); }
}

main().catch((e) => adicionar("Não consegui iniciar: " + erroHumano(e) + " Feche e abra o app de novo.", "jarvis erro"));
