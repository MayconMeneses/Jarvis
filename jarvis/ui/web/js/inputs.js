  function autosize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  input.addEventListener("input", autosize);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  });
  document.getElementById("reset").addEventListener("click", async () => {
    if (busy) return;
    await window.pywebview.api.reset();
    log.textContent = "";
    add("jarvis", "Conversa nova. Em que posso ajudar?");
    showSuggestions();
    input.focus();
  });
