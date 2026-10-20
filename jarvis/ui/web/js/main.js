  window.addEventListener("pywebviewready", async () => {
    refreshStats();
    periodico(refreshStats, 3000);
    const typing = addTyping();
    const hello = await window.pywebview.api.greeting();
    typing.remove();
    add("jarvis", hello);
    try {  // falta de Claude Code ou git: explica o que muda em vez de falhar em silêncio
      (await window.pywebview.api.environment_notices()).forEach((n) => add("error", n));
    } catch (err) { /* o aviso é só um extra */ }
    showSuggestions();
    mic.hidden = !(await window.pywebview.api.voice_available());
  });
