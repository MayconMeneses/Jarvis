// Aba "PC" (cartões somente leitura, ver painel-pc-geral.js) e o campo opcional "PC pareado" (aba Cérebro). Tudo com textContent; o que vem do PC é texto de terceiros.
import { montar as montarPainel } from "./painel-pc-geral.js";
import { Atualizador } from "./pc-atualizador.js";

const $ = (id) => document.getElementById(id);
const el = (tag, props = {}, ...filhos) => { const n = Object.assign(document.createElement(tag), props); n.append(...filhos); return n; };

function montarAba() {
  const botao = el("button", { type: "button", textContent: "PC" });
  botao.dataset.aba = "agenda";  // o id interno continua "agenda": o main.js abre a aba por ele
  $("abas").append(botao);
  const secao = el("section", { id: "agenda", className: "aba", hidden: true }, el("h2", { textContent: "Seu PC (somente leitura)" }));
  $("app").append(secao);
  return secao;
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

export function ligarPc({ pc, avisar, intervaloMs = 30000 }) {
  const secao = montarAba();
  montarPareamento();
  const painel = montarPainel(secao, { pc });

  async function estado() {
    const p = await pc.pareamento();
    $("pc-desparear").hidden = !p;
    $("pc-status").textContent = p ? `Pareado com ${new URL(p.url).host}.` : "Não pareado.";
    return p;
  }

  const atualizar = async () => { await estado(); return painel.atualizar(); };
  // Atualização leve: só com a aba PC aberta, página visível e PC pareado.
  const auto = new Atualizador({ atualizar: painel.atualizar, visivel: () => document.visibilityState === "visible", ativo: () => !secao.hidden, pareado: () => pc.pareado(), intervaloMs });
  auto.iniciar();
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") auto.tick(); });

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
  $("pc-desparear").addEventListener("click", async () => { await pc.desparear(); avisar("Pareamento removido deste aparelho. Para revogar no PC, use a lista de aparelhos da janela."); await estado(); painel.atualizar(); });
  estado();
  return atualizar;  // chamado ao abrir a aba PC
}
