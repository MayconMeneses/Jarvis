  const log = document.getElementById("log");
  const input = document.getElementById("input");
  const form = document.getElementById("form");
  const send = document.getElementById("send");
  let busy = false;

  const SUGGESTIONS = ["Como está meu PC?", "Notícias de tecnologia", "Tem vagas para mim?", "Resuma meus e-mails"];

  // Marcações da régua do reator (desenhadas uma vez).
  (function drawTicks() {
    const g = document.getElementById("ticks");
    for (let i = 0; i < 72; i++) {
      const a = (i / 72) * Math.PI * 2, long = i % 6 === 0;
      const r1 = 92, r2 = long ? 99 : 96;
      const l = document.createElementNS("http://www.w3.org/2000/svg", "line");
      l.setAttribute("x1", 100 + r1 * Math.cos(a)); l.setAttribute("y1", 100 + r1 * Math.sin(a));
      l.setAttribute("x2", 100 + r2 * Math.cos(a)); l.setAttribute("y2", 100 + r2 * Math.sin(a));
      l.setAttribute("stroke-width", long ? 1.6 : .8);
      g.appendChild(l);
    }
  })();

  function now() { return new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); }
  function scrollDown() { log.scrollTop = log.scrollHeight; }
  function setOrb(state) { document.body.dataset.state = state; }

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
