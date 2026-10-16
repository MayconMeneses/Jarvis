  const CHANGE_LABEL = { novo: "novo", modificado: "alterado", apagado: "apagado", modificado_sem_backup: "alterado (sem cópia anterior)" };

  function renderDiff(text) {
    const pre = document.createElement("pre");
    pre.className = "diff";
    pre.setAttribute("aria-label", "Diferenças no código");
    for (const line of (text || "(sem diff para mostrar)").split("\n")) {
      const span = document.createElement("span");
      span.className = /^(\+\+\+|---|diff )/.test(line) ? "file" : line.startsWith("+") ? "add"
        : line.startsWith("-") ? "del" : line.startsWith("@@") ? "hunk" : "";
      span.textContent = line + "\n";
      pre.appendChild(span);
    }
    return pre;
  }

  function addReviewCard(r) {
    hideSuggestions();
    const card = document.createElement("section");
    card.className = "card review";
    card.setAttribute("aria-label", "Revisar mudanças do Claude Code");
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = "Revise as mudanças · projeto " + r.projeto;
    const list = document.createElement("ul");
    list.className = "files";
    for (const f of r.arquivos || []) {
      const li = document.createElement("li");
      const b = document.createElement("b");
      b.textContent = f.arquivo;
      li.append(b, " — " + (CHANGE_LABEL[f.tipo] || f.tipo));
      list.appendChild(li);
    }
    const buttons = document.createElement("div");
    buttons.className = "buttons";
    const keep = document.createElement("button");
    keep.type = "button"; keep.className = "primary"; keep.textContent = "Manter";
    const undo = document.createElement("button");
    undo.type = "button"; undo.textContent = "Desfazer";
    buttons.append(keep, undo);
    card.append(label, list, renderDiff(r.diff));
    if (r.propria) {
      const hint = document.createElement("p");
      hint.className = "why";
      hint.textContent = "É o código da própria Jarvis: ao manter, rodo os testes e o benchmark e só depois ofereço reiniciar.";
      card.appendChild(hint);
    }
    card.appendChild(buttons);
    log.appendChild(card);
    scrollDown();

    async function decide(keepIt) {
      keep.disabled = undo.disabled = true;
      const res = await window.pywebview.api.review_run(r.id, keepIt);
      buttons.remove();
      card.classList.add("done");
      card.dataset.status = res.status === "mantida" ? "executada" : res.status === "desfeita" ? "recusada" : "falhou";
      label.textContent = { mantida: "Mudanças mantidas", desfeita: "Mudanças desfeitas" }[res.status] || "Não foi possível";
      const out = document.createElement("p");
      out.className = "outcome";
      out.textContent = res.resultado;
      card.appendChild(out);
    }
    keep.addEventListener("click", () => decide(true));
    undo.addEventListener("click", () => decide(false));
  }
