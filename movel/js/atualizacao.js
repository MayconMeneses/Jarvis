// Versão nova do app: o service worker novo assume sozinho, mas a página aberta ainda roda o código velho.
// Avisamos com um botão (sem recarregar de surpresa: a pessoa pode estar escrevendo) e checamos ao voltar para o app.
// Na primeira instalação (sem controlador antes) não há o que avisar.
export const precisaAvisar = (tinhaControle, jaAvisou) => Boolean(tinhaControle && !jaAvisou);

export function ligarAtualizacao(nav = navigator, doc = document, janela = window) {
  if (!nav.serviceWorker) return;
  const tinha = Boolean(nav.serviceWorker.controller);
  let avisado = false;
  nav.serviceWorker.addEventListener("controllerchange", () => {
    if (!precisaAvisar(tinha, avisado)) return;
    avisado = true;
    const barra = doc.createElement("div");
    barra.id = "nova-versao";
    barra.setAttribute("role", "status");
    const botao = Object.assign(doc.createElement("button"), { type: "button", textContent: "Nova versão pronta: tocar para atualizar" });
    botao.addEventListener("click", () => janela.location.reload());
    barra.append(botao);
    doc.body.append(barra);
  });
  doc.addEventListener("visibilitychange", () => { if (!doc.hidden) nav.serviceWorker.getRegistration().then((r) => r?.update()).catch(() => {}); });
}
