  window.addEventListener("pywebviewready", async () => {
    refreshStats();
    setInterval(refreshStats, 3000);
    const typing = addTyping();
    const hello = await window.pywebview.api.greeting();
    typing.remove();
    add("jarvis", hello);
    showSuggestions();
    mic.hidden = !(await window.pywebview.api.voice_available());
  });
