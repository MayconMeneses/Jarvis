// Se o Safari matar o app em segundo plano, ao voltar a Jarvis lembra a aba aberta e o texto que estava sendo escrito.
// Guarda só isso (nunca campos de senha), no localStorage; se ele não existir, tudo continua funcionando.
const CHAVE = "jarvis-retomada";
const MAX = 4000;

export class Retomada {
  constructor(armazem = globalThis.localStorage) { this.armazem = armazem; }
  ler() {
    try { const v = JSON.parse(this.armazem.getItem(CHAVE) || "{}"); return { aba: typeof v.aba === "string" ? v.aba : "", texto: typeof v.texto === "string" ? v.texto : "" }; }
    catch { return { aba: "", texto: "" }; }
  }
  gravar(parte) {
    try {
      const novo = { ...this.ler(), ...parte };
      novo.texto = novo.texto.slice(0, MAX);
      if (!novo.aba && !novo.texto) this.armazem.removeItem(CHAVE); else this.armazem.setItem(CHAVE, JSON.stringify(novo));
    } catch { /* cheio ou bloqueado: sem retomada, sem problema */ }
  }
}

export function ligarRetomada({ campo, abas, retomada = new Retomada(), doc = document }) {
  const salvo = retomada.ler();
  if (salvo.texto && !campo.value) campo.value = salvo.texto;
  if (salvo.aba && salvo.aba !== "conversa") abas.find((b) => b.dataset.aba === salvo.aba)?.click();
  campo.addEventListener("input", () => retomada.gravar({ texto: campo.value }));
  campo.form?.addEventListener("submit", () => retomada.gravar({ texto: "" }));
  abas.forEach((b) => b.addEventListener("click", () => retomada.gravar({ aba: b.dataset.aba })));
  doc.addEventListener("visibilitychange", () => { if (doc.hidden) retomada.gravar({ texto: campo.value }); });
}
