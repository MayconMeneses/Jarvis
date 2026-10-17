// Jarvis do celular: junta memória, conhecimento, motor de regras e (se ligado) o cérebro de IA do aparelho.
import { avisos } from "./proativo.js";
import { adicionar, atualizar, falar, ligarDitado, pensando } from "./chat.js";
import { Cerebro } from "./cerebro.js";
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
  const motor = new Motor({ saber, memoria, buscar: (url) => fetch(url) });
  const cerebro = new Cerebro();
  const historico = [];
  const nome = async () => (await memoria.meta("nome")) || "Maycon";

  async function perguntarIA(texto) {
    const dados = (await motor.consultarAntes(texto)) || "";
    const sistema = await contexto.sistema({ saber, memoria, pergunta: texto, nome: await nome(), dados });
    const mensagens = [{ role: "system", content: sistema }, ...contexto.historico(historico)];
    const bolha = adicionar("…", "jarvis", cerebro.modelo);
    pensando(true, "IA pensando…");
    try {
      const resposta = await cerebro.perguntar(mensagens, (parcial) => atualizar(bolha, parcial));
      atualizar(bolha, resposta || "Não consegui responder.");
      return resposta;
    } finally { pensando(false); }
  }

  async function enviar(texto) {
    texto = texto.trim();
    if (!texto) return;
    adicionar(texto, "eu");
    $("texto").value = "";
    historico.push({ role: "user", content: texto });
    await memoria.diario(`Pedido: ${texto.slice(0, 200)}`);
    pensando(true);
    let resposta;
    try {
      resposta = await motor.responder(texto);  // regras primeiro: dados exatos, instantâneo, sem gastar bateria
      if (resposta === null && cerebro.ligado()) { pensando(false); resposta = await perguntarIA(texto); }
      else {
        if (resposta === null) resposta = await motor.fallback(texto);
        adicionar(resposta, "jarvis");
      }
    } catch (e) {
      adicionar("Algo deu errado: " + e.message, "jarvis erro");
      resposta = "";
    } finally { pensando(false); }
    historico.push({ role: "assistant", content: resposta });
    falar(resposta);
  }

  $("form").addEventListener("submit", (ev) => { ev.preventDefault(); enviar($("texto").value); });
  document.querySelectorAll("#atalhos button").forEach((b) => b.addEventListener("click", () => enviar(b.dataset.texto)));
  ligarDitado(enviar);

  const aoAbrirMemoria = ligarMemoria(memoria, (t) => adicionar(t, "aviso"));
  const religar = ligarCerebro(cerebro, memoria, (t) => adicionar(t, "aviso"));
  document.querySelectorAll("#abas button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll("#abas button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
    document.querySelectorAll(".aba").forEach((a) => { a.hidden = a.id !== b.dataset.aba; });
    if (b.dataset.aba === "memoria") aoAbrirMemoria();
  }));

  adicionar("Olá! Eu sou a Jarvis e rodo **só neste celular**: minha memória e meu cérebro ficam aqui. Diga \"ajuda\" para ver o que sei fazer.", "jarvis");
  for (const aviso of await avisos({ memoria, saber, nome: await nome() })) adicionar(aviso, "jarvis aviso");
  religar();
  if ("serviceWorker" in navigator && window.isSecureContext) navigator.serviceWorker.register("sw.js").catch(() => {});
}

main().catch((e) => adicionar("Não consegui iniciar: " + e.message, "jarvis erro"));
