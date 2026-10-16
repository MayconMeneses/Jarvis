  function addActionCard(action) {
    const card = document.createElement("section");
    card.className = "card";
    card.setAttribute("aria-label", "Ação aguardando sua aprovação");
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = "Aguardando sua aprovação";
    const what = document.createElement("p");
    what.textContent = action.descricao;
    const why = document.createElement("p");
    why.className = "why";
    why.textContent = "Motivo: " + action.motivo;
    const buttons = document.createElement("div");
    buttons.className = "buttons";
    const ok = document.createElement("button");
    ok.type = "button"; ok.className = "primary"; ok.textContent = "Aprovar";
    const no = document.createElement("button");
    no.type = "button"; no.textContent = "Recusar";
    buttons.append(ok, no);
    card.append(label, what, why, buttons);
    log.appendChild(card);
    scrollDown();

    async function decide(approve) {
      ok.disabled = no.disabled = true;
      const res = await window.pywebview.api.decide(action.id, approve);
      buttons.remove();
      card.classList.add("done");
      card.dataset.status = res.status;
      label.textContent = { executada: "Aprovada e executada", recusada: "Recusada", falhou: "Não foi possível" }[res.status] || res.status;
      const out = document.createElement("p");
      out.className = "outcome";
      out.textContent = res.resultado;
      card.appendChild(out);
    }
    ok.addEventListener("click", () => decide(true));
    no.addEventListener("click", () => decide(false));
  }
