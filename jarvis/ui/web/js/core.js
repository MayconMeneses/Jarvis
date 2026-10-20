  const log = document.getElementById("log");
  const input = document.getElementById("input");
  const form = document.getElementById("form");
  const send = document.getElementById("send");
  let busy = false;

  const SUGGESTIONS = ["Como está meu PC?", "Notícias de tecnologia", "Tem vagas para mim?", "Resuma meus e-mails"];

  function now() { return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); }
  function scrollDown() { log.scrollTop = log.scrollHeight; }
  function setOrb(state) { document.body.dataset.state = state; if (window.Orbe) window.Orbe.estado(state); }

  function tickClock() { document.getElementById("clock").textContent = now(); }
  tickClock();
  setInterval(tickClock, 15000);

  async function refreshStats() {
    try {
      const s = await window.pywebview.api.system_stats();
      for (const k of ["cpu", "ram", "disco"]) {
        const bar = document.getElementById("g-" + k);
        bar.style.width = s[k] + "%";
        bar.className = s[k] >= 90 ? "crit" : s[k] >= 75 ? "warn" : "";
        document.getElementById("v-" + k).textContent = s[k] + "%";
      }
    } catch (e) { /* janela fechando */ }
  }
