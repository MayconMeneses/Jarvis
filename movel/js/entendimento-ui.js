// Botões e cartões que acompanham uma resposta do entendimento: "Você quis dizer" (opções), atalhos (abrir painel, modo foco, pesquisar)
// e o cartão Guardar/Descartar de um atalho ensinado. Só textContent (o texto pode ter vindo do que o usuário digitou).
const el = (tag, texto, classe) => { const e = document.createElement(tag); if (texto) e.textContent = texto; if (classe) e.className = classe; return e; };
const botao = (rotulo) => Object.assign(el("button", rotulo), { type: "button" });

// `acoes`: { escolher(frase, id) -> {texto, widget}, enviar(texto), abrir({aba, foco}), foco(), apagarAprendizado(), confirmarAtalho(p) -> texto, mostrar(texto, widget) }
export function montarWidget(widget, bolha, acoes) {
  if (!widget || !bolha) return null;
  const linha = el("div", "", "linha entendimento");
  const feitos = [], travar = () => feitos.forEach((b) => { b.disabled = true; });
  const adicionar = (rotulo, fazer) => {
    const b = botao(rotulo);
    feitos.push(b);
    b.addEventListener("click", async () => { travar(); try { await fazer(); } catch (e) { acoes.mostrar(`Não consegui: ${e.message}`); } });
    linha.append(b);
  };
  if (widget.tipo === "proposta") {
    linha.setAttribute("role", "group");
    linha.setAttribute("aria-label", "Guardar este atalho?");
    adicionar("Guardar", async () => { linha.replaceChildren(el("small", await acoes.confirmarAtalho(widget))); });
    adicionar("Descartar", async () => { linha.replaceChildren(el("small", "Descartado. Nada foi guardado.")); });
  } else {
    for (const o of widget.opcoes || []) adicionar(o.rotulo, async () => { const r = await acoes.escolher(widget.frase, o.id); acoes.mostrar(r.texto, r.widget); });
    for (const b of widget.botoes || []) {
      if (b.enviar) adicionar(b.rotulo, () => acoes.enviar(b.enviar));
      else if (b.abrir) adicionar(b.rotulo, () => acoes.abrir(b.abrir));
      else if (b.foco) adicionar(b.rotulo, () => acoes.foco());
      else if (b.apagarAprendizado) adicionar(b.rotulo, async () => acoes.mostrar(await acoes.apagarAprendizado()));
    }
  }
  if (!feitos.length) return null;
  bolha.append(linha);
  return linha;
}
