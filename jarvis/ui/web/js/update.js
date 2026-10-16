  // ── atualização automática ────────────────────────────────────────────
  // Chega quando uma versão nova já foi baixada e conferida (SHA-256).
  function addUpdateCard(u) {
    hideSuggestions();
    const card = document.createElement("section");
    card.className = "card";
    card.setAttribute("aria-label", "Atualização da Jarvis");
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = "Atualização " + u.versao + " pronta";
    const info = document.createElement("p");
    info.textContent = "Ela será instalada sozinha na próxima vez que você abrir a Jarvis.";
    card.append(label, info);
    if (u.notas) {
      const notes = document.createElement("p");
      notes.className = "why";
      notes.textContent = u.notas;
      card.appendChild(notes);
    }
    const buttons = document.createElement("div");
    buttons.className = "buttons";
    const outcome = document.createElement("p");
    outcome.className = "outcome";
    const now = document.createElement("button");
    now.type = "button"; now.className = "primary"; now.textContent = "Atualizar agora";
    now.addEventListener("click", async () => {
      now.disabled = true;
      outcome.textContent = "Atualizando… a Jarvis fecha e abre sozinha.";
      const res = await window.pywebview.api.install_update();
      if (!res.ok) outcome.textContent = "Não foi possível instalar agora. Tente de novo mais tarde.";
    });
    const later = document.createElement("button");
    later.type = "button"; later.textContent = "Depois";
    later.addEventListener("click", () => buttons.remove());
    buttons.append(now, later);
    card.append(buttons, outcome);
    log.appendChild(card);
    scrollDown();
  }
