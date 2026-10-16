  const CRITERIA = { coerencia: "coerência", clareza: "clareza", relevancia: "relevância", fidelidade: "fidelidade", fluidez: "fluidez" };

  function showResult(res, originalText, files = []) {
    if (res.error) addError(res.error, originalText, files);
    else {
      const q = res.qualidade;
      const el = add("jarvis", res.text, "via " + res.brain + (q && q.media != null ? ` · qualidade ${q.media.toFixed(1)}/10` : ""));
      if (q) {
        el.querySelector(".meta").title = Object.entries(q.notas)
          .map(([k, v]) => `${CRITERIA[k] || k}: ${v == null ? "—" : v.toFixed(1)} (${q.motivos[k]})`).join("\n");
      }
      (res.actions || []).forEach(addActionCard);
    }
  }

  // Eventos do ciclo de voz e das tarefas, enviados pelo Python.
  const voiceStatus = document.getElementById("voice-status");
  const mic = document.getElementById("mic");
  const STATUS_TO_ORB = { "Ouvindo…": "listening", "Transcrevendo…": "thinking", "Pensando…": "thinking", "Falando…": "speaking" };
  window.onVoice = (ev) => {
    if (ev.status !== undefined) {
      voiceStatus.textContent = ev.status;
      if (!busy) setOrb(STATUS_TO_ORB[ev.status] || "idle");
    }
    if (ev.listening !== undefined) mic.classList.toggle("on", ev.listening);
    if (ev.user) add("user", ev.user, "por voz");
    if (ev.answer) showResult(ev.answer);
    if (ev.aviso) add("jarvis task", ev.aviso, "a Jarvis lembrou");
    if (ev.task) add("jarvis task", ev.task, "tarefa do Claude Code");
    if (ev.review) addReviewCard(ev.review);
    if (ev.verify) addVerifyCard(ev.verify);
    if (ev.update) addUpdateCard(ev.update);
  };
  mic.addEventListener("click", () => window.pywebview.api.listen_now());
  document.getElementById("dash").addEventListener("click", async () => {
    const res = await window.pywebview.api.dashboard();
    if (res.error) add("error", res.error);
    else if (res.text) add("jarvis", res.text, "dashboard");
  });
