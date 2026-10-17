// Jarvis do celular: junta memória, conhecimento, motor de regras e (se ligado) o cérebro de IA do aparelho.
import { avisos } from "./proativo.js";
import { adicionar, atualizar, destravarFala, falar, ligarConversaPorVoz, ligarDitado, pensando } from "./chat.js";
import { Cerebro } from "./cerebro.js";
import { Nuvem } from "./nuvem.js";
import { ligarNuvem } from "./painel-nuvem.js";
import { Conversa } from "./conversa.js";
import * as contexto from "./contexto.js";
import { ArmazemIndexedDB, ArmazemMemoria, Memoria } from "./memoria.js";
import { Motor } from "./motor.js";
import { ligarCerebro } from "./painel-cerebro.js";
import { ligarMemoria } from "./painel-memoria.js";
import { Saber } from "./saber.js";

const $ = (id) => document.getElementById(id);

async function iniciarMemoria() {
  try {
    const armazem = new ArmazemIndexedDB();
    await armazem.chaves();  // falha cedo em modo privado
    if (navigator.storage?.persist) navigator.storage.persist();  // pede ao iPhone para não apagar a memória
    return new Memoria(armazem);
  } catch (e) {
    adicionar("Este navegador não deixa guardar dados (modo privado?). A memória vale só enquanto o app estiver aberto.", "aviso");
    return new Memoria(new ArmazemMemoria());
  }
}

async function main() {
  const saber = new Saber(await (await fetch("dados/saber.json")).json());
  const memoria = await iniciarMemoria();
  const nuvem = new Nuvem({ armazem: memoria.armazem });
  const motor = new Motor({ saber, memoria, buscar: (url, opcoes) => fetch(url, opcoes), brave: () => nuvem.brave() });
  const cerebro = new Cerebro();
  const conversa = new Conversa(memoria);
  const nome = async () => (await memoria.meta("nome")) || "Maycon";

  async function perguntarIA(texto) {
    const dados = (await motor.consultarAntes(texto)) || "";
    const sistema = await contexto.sistema({ saber, memoria, pergunta: texto, nome: await nome(), dados });
    const mensagens = [{ role: "system", content: sistema }, ...conversa.paraPrompt()];  // cabe no contexto do modelo, sempre
    const bolha = adicionar("…", "jarvis", cerebro.modelo);
    pensando(true, "IA pensando…");
    try {
      const resposta = await cerebro.perguntar(mensagens, (parcial) => atualizar(bolha, parcial), (aviso) => atualizar(bolha, aviso));
      atualizar(bolha, resposta || "Não consegui responder.");
      return resposta;
    } catch (e) {
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
      const r = await nuvem.perguntar([{ role: "system", content: sistema }, ...conversa.paraPrompt(9000)], (parcial) => atualizar(bolha, parcial));
      atualizar(bolha, r.texto);
      const nota = document.createElement("small");
      nota.textContent = r.provedor;
      bolha.appendChild(nota);
      return r.texto;
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

  const aoAbrirMemoria = ligarMemoria(memoria, (t) => adicionar(t, "aviso"));
  const religar = ligarCerebro(cerebro, memoria, (t) => adicionar(t, "aviso"));
  const aoAbrirNuvem = ligarNuvem(nuvem, memoria, (t) => adicionar(t, "aviso"));
  aoAbrirNuvem();
  document.querySelectorAll("#abas button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("#abas button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    document.querySelectorAll(".aba").forEach((a) => { a.hidden = a.id !== b.dataset.aba; });
    if (b.dataset.aba === "memoria") aoAbrirMemoria();
  }));

  const anterior = await conversa.carregar();
  if (anterior.length) {  // conversa contínua: ao reabrir (ou se o iPhone recarregar o app), ela continua de onde parou
    adicionar("Continuando de onde paramos:", "jarvis aviso");
    for (const m of anterior.slice(-12)) adicionar(m.content, m.role === "user" ? "eu" : "jarvis");
  } else {
    adicionar("Olá! Eu sou a Jarvis e rodo **só neste celular**: minha memória e meu cérebro ficam aqui. Pode escrever ou tocar em **Conversar por voz**. Diga \"ajuda\" para ver o que sei fazer.", "jarvis");
  }
  for (const aviso of await avisos({ memoria, saber, nome: await nome() })) adicionar(aviso, "jarvis aviso");
  religar();
  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => {});
}

main().catch((e) => adicionar("Não consegui iniciar: " + e.message, "jarvis erro"));
