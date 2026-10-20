  const log = document.getElementById("log");
  const input = document.getElementById("input");
  const form = document.getElementById("form");
  const send = document.getElementById("send");
  let busy = false;

  const SUGGESTIONS = ["Como está meu PC?", "Notícias de tecnologia", "Tem vagas para mim?", "Resuma meus e-mails"];

  function now() { return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); }
  function scrollDown() { log.scrollTop = log.scrollHeight; }
  function setOrb(state) { document.body.dataset.state = state; if (window.Orbe) window.Orbe.set({ estado: state }); }

  // Repete fn a cada ms, mas só com a janela visível (ela vive horas na bandeja): ao voltar, roda uma vez e retoma.
  function periodico(fn, ms) {
    let id = 0;
    const ligar = () => { if (!id) id = setInterval(fn, ms); };
    const parar = () => { clearInterval(id); id = 0; };
    document.addEventListener("visibilitychange", () => { if (document.hidden) parar(); else { fn(); ligar(); } });
    if (!document.hidden) ligar();
  }

  function tickClock() { document.getElementById("clock").textContent = now(); }
  tickClock();
  periodico(tickClock, 15000);

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
