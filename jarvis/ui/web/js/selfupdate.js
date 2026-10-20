  // ── verificação de uma melhoria no próprio código ─────────────────────
  // Chega depois de "Manter": testes + benchmark já rodaram em outro processo.
  function addVerifyCard(v) {
    hideSuggestions();
    const card = document.createElement("section");
    card.className = "card" + (v.aprovado ? "" : " failed");
    card.setAttribute("aria-label", "Resultado da verificação da melhoria");
    const label = document.createElement("p");
    label.className = "label";
    label.textContent = v.aprovado ? "Melhoria verificada"
      : (v.gate === "BLOCKED" ? "Verificação incompleta (não conta como aprovada)" : "Verificação reprovada");
    const tests = document.createElement("p");
    tests.textContent = "Testes: " + v.testes;
    card.append(label, tests);
    if ((v.pioras || []).length) {
      const worse = document.createElement("p");
      worse.className = "why";
      worse.textContent = "Piorou no benchmark: " + v.pioras.join(" · ");
      card.appendChild(worse);
    }
    const buttons = document.createElement("div");
    buttons.className = "buttons";
    const outcome = document.createElement("p");
    outcome.className = "outcome";
    if (v.aprovado) {
      const restart = document.createElement("button");
      restart.type = "button"; restart.className = "primary"; restart.textContent = "Reiniciar agora";
      restart.addEventListener("click", async () => {
        restart.disabled = true;
        outcome.textContent = "Reiniciando…";
        await window.pywebview.api.restart_jarvis();
      });
      const later = document.createElement("button");
      later.type = "button"; later.textContent = "Depois";
      later.addEventListener("click", () => buttons.remove());
      buttons.append(restart, later);
    } else {
      const revert = document.createElement("button");
      revert.type = "button"; revert.className = "primary"; revert.textContent = "Desfazer mudanças";
      revert.addEventListener("click", async () => {
        revert.disabled = true;
        const res = await window.pywebview.api.revert_run(v.id);
        buttons.remove();
        outcome.textContent = res.resultado;
      });
      const keepAnyway = document.createElement("button");
      keepAnyway.type = "button"; keepAnyway.textContent = "Manter assim";
      keepAnyway.addEventListener("click", () => buttons.remove());
      buttons.append(revert, keepAnyway);
    }
    card.append(buttons, outcome);
    log.appendChild(card);
    scrollDown();
  }
