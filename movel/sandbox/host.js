// Dentro do iframe isolado: recebe do app o código do Worker e os arquivos, cria o Worker e repassa as mensagens dele.
let trabalhador = null;
addEventListener("message", (ev) => {
  if (ev.source !== parent || trabalhador) return;  // só uma execução por ambiente, e só a pedido do app
  const { fonte, entrada } = ev.data || {};
  try {
    trabalhador = new Worker(URL.createObjectURL(new Blob([fonte], { type: "text/javascript" })));
    trabalhador.onmessage = (m) => parent.postMessage(m.data, "*");
    trabalhador.onerror = (e) => parent.postMessage({ tipo: "saida", linha: "[erro] " + e.message }, "*") || parent.postMessage({ tipo: "fim", ok: false }, "*");
    trabalhador.postMessage(entrada);
  } catch (e) {
    parent.postMessage({ tipo: "saida", linha: "[erro] " + e.message }, "*");
    parent.postMessage({ tipo: "fim", ok: false }, "*");
  }
});
parent.postMessage({ tipo: "pronto" }, "*");
