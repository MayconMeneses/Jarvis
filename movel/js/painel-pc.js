// Painel "Agenda e e-mails" (aba Agenda) e o campo opcional "PC pareado" (aba Cérebro). Tudo com textContent; o que vem do PC é texto de terceiros.
import { OFFLINE } from "./pc-pareado.js";
import { textoAgenda, textoEmails } from "./motor-pc.js";

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };

function montarAba() {
  const botao = el("button", { type: "button", textContent: "Agenda" });
  botao.dataset.aba = "agenda";
  botao.setAttribute("aria-selected", "false");
  $("abas").append(botao);
  const secao = el("section", { id: "agenda", className: "aba", hidden: true },
    el("h2", { textContent: "Agenda e e-mails" }),
    el("p", { id: "pc-aviso", className: "nota", role: "status" }),
    el("div", { className: "linha" }, el("button", { type: "button", id: "pc-atualizar", textContent: "Atualizar" })),
    el("h2", { textContent: "Agenda" }), el("div", { id: "pc-agenda", className: "msg jarvis" }),
    el("h2", { textContent: "E-mails" }), el("div", { id: "pc-emails", className: "msg jarvis" }),
    el("p", { className: "nota", textContent: "Somente leitura: vem do seu PC pareado, sem corpo de e-mail e sem links. Com o PC desligado ou fora da rede, mostro a última cópia, com a hora." }));
  $("app").append(secao);
}

function montarPareamento() {
  const bloco = el("details", { id: "pc-bloco" },
    el("summary", { textContent: "PC pareado (opcional): agenda e e-mails" }),
    el("p", { className: "nota", textContent: "O app funciona sem isto. Para ver a agenda e os e-mails do seu PC aqui: (1) no PC, ligue o \"Jarvis no celular\" com o Tailscale e toque em gerar código; (2) informe abaixo o endereço https que a janela mostra e o código de 6 dígitos (vale 5 minutos). O celular guarda só um token neste aparelho, fora da cópia de segurança, e só consegue LER; revogue quando quiser na janela do PC." }),
    el("label", { htmlFor: "pc-url", textContent: "Endereço do PC (https://…)" }),
    el("input", { id: "pc-url", autocomplete: "off", spellcheck: false, placeholder: "https://seu-pc.tailnet.ts.net:8765", inputMode: "url" }),
    el("label", { htmlFor: "pc-codigo", textContent: "Código de 6 dígitos" }),
    el("input", { id: "pc-codigo", autocomplete: "off", inputMode: "numeric", maxLength: 6 }),
    el("div", { className: "linha" }, el("button", { type: "button", id: "pc-parear", textContent: "Parear" }), el("button", { type: "button", id: "pc-desparear", textContent: "Desparear", hidden: true })),
    el("p", { id: "pc-status", role: "status" }));
  const alvo = $("cerebro").querySelector("details");  // antes de "Instalar como app"
  $("cerebro").insertBefore(bloco, alvo);
}

export function ligarPc({ pc, avisar }) {
  montarAba();
  montarPareamento();

  async function estado() {
    const p = await pc.pareamento();
    $("pc-desparear").hidden = !p;
    $("pc-status").textContent = p ? `Pareado com ${new URL(p.url).host}.` : "Não pareado.";
    return p;
  }

  async function atualizar() {
    const p = await estado();
    if (!p) { $("pc-aviso").textContent = "Pareie com o PC na aba Cérebro (PC pareado) para ver a agenda e os e-mails."; $("pc-agenda").replaceChildren(); $("pc-emails").replaceChildren(); return; }
    $("pc-aviso").textContent = "Atualizando…";
    const [ag, em] = await Promise.all([pc.obter("agenda"), pc.obter("emails")]);
    const mostrar = (id, r, fmt) => {
      const alvo = $(id);
      alvo.replaceChildren();
      for (const linha of (r.ok ? fmt(r) : r.erro).split("\n")) alvo.append(el("p", { textContent: linha.replace(/\*\*/g, "") }));
    };
    mostrar("pc-agenda", ag, textoAgenda);
    mostrar("pc-emails", em, textoEmails);
    const copia = [ag, em].find((r) => r.ok && r.doCache);
    $("pc-aviso").textContent = copia ? `${copia.erro || OFFLINE} Mostrando a cópia de ${new Date(copia.quando).toLocaleString("pt-BR")}.`
      : ag.ok || em.ok ? `Atualizado às ${new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}.` : (ag.erro || OFFLINE);
  }

  $("pc-atualizar").addEventListener("click", atualizar);
  $("pc-parear").addEventListener("click", async () => {
    $("pc-parear").disabled = true;
    $("pc-status").textContent = "Pareando…";
    try {
      const url = await pc.parear($("pc-url").value, $("pc-codigo").value);
      $("pc-codigo").value = "";
      avisar(`Pareado com o PC (${new URL(url).host}). Só leitura.`);
      await estado();
    } catch (e) { $("pc-status").textContent = "Não consegui parear: " + e.message; } finally { $("pc-parear").disabled = false; }
  });
  $("pc-desparear").addEventListener("click", async () => { await pc.desparear(); avisar("Pareamento removido deste aparelho. Para revogar no PC, use a lista de aparelhos da janela."); await estado(); });
  estado();
  return atualizar;  // chamado ao abrir a aba Agenda
}
