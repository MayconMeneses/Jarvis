  function setBusy(on) {
    busy = on;
    send.disabled = on;
    log.setAttribute("aria-busy", on ? "true" : "false");
    setOrb(on ? "thinking" : "idle");
  }

  async function ask(text, echo, files = []) {
    if ((!text && !files.length) || busy) return;
    if (echo) add("user", text + (files.length ? (text ? "\n" : "") + "📎 " + files.map((f) => f.nome).join(", ") : ""));
    setBusy(true);
    const typing = addTyping();
    try {
      const res = await window.pywebview.api.send(text, files.map((f) => f.id));
      typing.remove();
      showResult(res, text, files);
    } catch (err) {
      typing.remove();
      addError("Falha ao falar com o núcleo da Jarvis: " + err, text, files);
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  function submit() {
    const text = input.value.trim();
    if ((!text && !pending.length) || busy) return;
    const files = pending;
    pending = [];
    renderChips();
    input.value = "";
    autosize();
    ask(text, true, files);
  }
