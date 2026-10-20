  // ── mapa da memória (Second Brain): Canvas 2D puro, um nó por nota ─────────────
  // Texto de nota (de terceiros) só entra por fillText/textContent: nunca como HTML.
  const MemoriaGrafo = (() => {
    const canvas = document.getElementById("mem-canvas");
    const legenda = document.getElementById("mem-legenda");
    const ctx = canvas.getContext("2d");
    const reduzir = window.matchMedia("(prefers-reduced-motion: reduce)");
    const FPS_ATIVO = 30, FPS_OCIOSO = 15, OCIOSO_MS = 4000, MAX_PULSOS = 5;
    let nos = [], arestas = [], areas = {}, aberto = false, rodando = false;
    let largura = 0, altura = 0, dpr = 1, ultimoQuadro = 0, ultimaAcao = 0, sobre = -1, foco = -1, pulsos = [];
    let aoAbrir = () => {};

    function hash(texto) {  // número estável 0..1 para espalhar os nós sem sorteio a cada abertura
      let h = 2166136261;
      for (let i = 0; i < texto.length; i++) h = Math.imul(h ^ texto.charCodeAt(i), 16777619);
      return ((h >>> 0) % 10000) / 10000;
    }

    function posicionar(dados) {
      const ids = dados.areas.map((a) => a.id), setor = (Math.PI * 2) / ids.length;
      const maxGrau = Math.max(1, ...dados.nos.map((n) => n.grau));
      nos = dados.nos.map((n) => {
        const base = ids.indexOf(n.area) * setor - Math.PI / 2;
        const ang = base + setor * (0.12 + 0.76 * hash(n.ref + "a"));
        const raio = 0.3 + 0.62 * (1 - 0.55 * n.grau / maxGrau) * (0.55 + 0.45 * hash(n.ref + "r"));
        return { ref: String(n.ref), area: n.area, grau: n.grau, x: Math.cos(ang) * raio, y: Math.sin(ang) * raio,
                 r: 2.5 + Math.min(7, n.grau * 1.2), fase: hash(n.ref + "f") * 6.28 };
      });
      arestas = dados.arestas.filter(([a, b]) => nos[a] && nos[b]);
      areas = Object.fromEntries(dados.areas.map((a) => [a.id, a]));
      pulsos = [];
    }

    function desenharLegenda(dados) {
      const contagem = {};
      dados.nos.forEach((n) => { contagem[n.area] = (contagem[n.area] || 0) + 1; });
      legenda.replaceChildren(...dados.areas.map((a) => {
        const li = document.createElement("li");
        const marca = document.createElement("i");
        marca.style.background = a.cor;
        li.append(marca, `${a.nome} (${contagem[a.id] || 0})`);
        return li;
      }));
      canvas.setAttribute("aria-label", `Mapa da memória: ${dados.nos.length} nota(s) em ${dados.areas.length} áreas. `
        + "Setas escolhem a nota, Enter abre.");
    }

    function ajustar() {
      dpr = Math.min(2, window.devicePixelRatio || 1);
      largura = canvas.clientWidth; altura = canvas.clientHeight;
      canvas.width = Math.max(1, Math.round(largura * dpr));
      canvas.height = Math.max(1, Math.round(altura * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    const escala = () => Math.min(largura, altura) / 2 - 18;
    const tela = (n) => [largura / 2 + n.x * escala(), altura / 2 + n.y * escala()];

    function ponto(a, b, t) {  // ponto da curva quadrática da aresta a-b, com o controle puxado para o núcleo
      const [x1, y1] = tela(a), [x2, y2] = tela(b), cx = (x1 + x2) / 2 * 0.72 + largura / 2 * 0.28, cy = (y1 + y2) / 2 * 0.72 + altura / 2 * 0.28;
      const u = 1 - t;
      return [u * u * x1 + 2 * u * t * cx + t * t * x2, u * u * y1 + 2 * u * t * cy + t * t * y2];
    }

    function desenharArestas() {
      ctx.lineWidth = 1;
      for (const [i, j] of arestas) {
        const a = nos[i], b = nos[j], [x1, y1] = tela(a), [x2, y2] = tela(b);
        const cx = (x1 + x2) / 2 * 0.72 + largura / 2 * 0.28, cy = (y1 + y2) / 2 * 0.72 + altura / 2 * 0.28;
        const ativa = i === sobre || j === sobre || i === foco || j === foco;
        ctx.strokeStyle = ativa ? "rgba(223,244,255,.75)" : "rgba(127,163,184,.22)";
        ctx.beginPath(); ctx.moveTo(x1, y1); ctx.quadraticCurveTo(cx, cy, x2, y2); ctx.stroke();
      }
    }

    function desenharPulsos(agora, parado) {
      if (parado || !arestas.length) return;
      while (pulsos.length < Math.min(MAX_PULSOS, arestas.length)) {
        pulsos.push({ e: Math.floor(Math.random() * arestas.length), t: Math.random(), v: 0.0004 + Math.random() * 0.0004 });
      }
      for (const p of pulsos) {
        p.t += p.v * 33;
        if (p.t >= 1) { p.t = 0; p.e = Math.floor(Math.random() * arestas.length); }
        const [i, j] = arestas[p.e], [x, y] = ponto(nos[i], nos[j], p.t);
        ctx.fillStyle = areas[nos[i].area].cor;
        ctx.globalAlpha = 0.9; ctx.beginPath(); ctx.arc(x, y, 2, 0, 6.283); ctx.fill(); ctx.globalAlpha = 1;
      }
    }

    function desenharNucleo(agora, parado) {
      const pulso = parado ? 0.5 : 0.5 + 0.5 * Math.sin(agora / 600), x = largura / 2, y = altura / 2, r = 14 + 4 * pulso;
      const g = ctx.createRadialGradient(x, y, 0, x, y, r * 3);
      g.addColorStop(0, "rgba(191,242,255,.95)"); g.addColorStop(0.35, "rgba(63,208,255,.45)"); g.addColorStop(1, "rgba(63,208,255,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r * 3, 0, 6.283); ctx.fill();
      ctx.fillStyle = "#bff2ff"; ctx.beginPath(); ctx.arc(x, y, r * 0.5, 0, 6.283); ctx.fill();
    }

    function rotulo(n, x, y) {
      let texto = n.ref.length > 42 ? n.ref.slice(0, 41) + "…" : n.ref;
      ctx.font = "12px 'Segoe UI', system-ui, sans-serif";
      const w = ctx.measureText(texto).width + 10, bx = Math.min(Math.max(2, x - w / 2), largura - w - 2), by = y - n.r - 22 < 2 ? y + n.r + 6 : y - n.r - 22;
      ctx.fillStyle = "rgba(4,7,12,.88)"; ctx.fillRect(bx, by, w, 18);
      ctx.strokeStyle = areas[n.area].cor; ctx.strokeRect(bx + 0.5, by + 0.5, w - 1, 17);
      ctx.fillStyle = "#dff4ff"; ctx.textBaseline = "middle"; ctx.fillText(texto, bx + 5, by + 9);
    }

    function desenhar(agora) {
      const parado = reduzir.matches;
      ctx.clearRect(0, 0, largura, altura);
      if (!nos.length) {
        desenharNucleo(agora, true);
        ctx.fillStyle = "#7fa3b8"; ctx.font = "13px 'Segoe UI', system-ui, sans-serif"; ctx.textAlign = "center";
        ctx.fillText("Nada guardado ainda.", largura / 2, altura / 2 + 46); ctx.textAlign = "start";
        return;
      }
      desenharArestas();
      desenharPulsos(agora, parado);
      desenharNucleo(agora, parado);
      nos.forEach((n, i) => {
        const [x, y] = tela(n), cor = areas[n.area].cor, destaque = i === sobre || i === foco;
        const respira = parado ? 0 : Math.sin(agora / 900 + n.fase) * 0.6;
        ctx.fillStyle = cor; ctx.globalAlpha = destaque ? 1 : 0.85;
        ctx.beginPath(); ctx.arc(x, y, n.r + respira + (destaque ? 2 : 0), 0, 6.283); ctx.fill(); ctx.globalAlpha = 1;
        if (destaque) { ctx.strokeStyle = "#dff4ff"; ctx.lineWidth = 1.5; ctx.stroke(); }
      });
      const alvo = sobre >= 0 ? sobre : foco;
      if (alvo >= 0) rotulo(nos[alvo], ...tela(nos[alvo]));
    }

    function quadro(agora) {
      if (!rodando) return;
      if (document.hidden || !aberto) { rodando = false; return; }
      const intervalo = 1000 / (agora - ultimaAcao < OCIOSO_MS ? FPS_ATIVO : FPS_OCIOSO);
      if (agora - ultimoQuadro >= intervalo) { ultimoQuadro = agora; desenhar(agora); }
      requestAnimationFrame(quadro);
    }

    function retomar() {
      if (reduzir.matches || document.hidden || !aberto) { if (aberto && !document.hidden) desenhar(performance.now()); return; }
      if (!rodando) { rodando = true; requestAnimationFrame(quadro); }
    }

    function acharNo(ev) {
      const r = canvas.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
      let melhor = -1, dist = 1e9;
      nos.forEach((n, i) => { const [x, y] = tela(n), d = Math.hypot(x - mx, y - my); if (d < n.r + 7 && d < dist) { melhor = i; dist = d; } });
      return melhor;
    }

    function tocou() { ultimaAcao = performance.now(); retomar(); }
    canvas.addEventListener("pointermove", (ev) => {
      const i = acharNo(ev);
      canvas.style.cursor = i >= 0 ? "pointer" : "default";
      if (i !== sobre) { sobre = i; if (reduzir.matches) desenhar(performance.now()); }
      tocou();
    });
    canvas.addEventListener("pointerleave", () => { sobre = -1; tocou(); if (reduzir.matches) desenhar(performance.now()); });
    canvas.addEventListener("click", (ev) => { const i = acharNo(ev); if (i >= 0) aoAbrir(nos[i].ref); });
    canvas.addEventListener("keydown", (ev) => {
      if (!nos.length) return;
      if (ev.key === "ArrowRight" || ev.key === "ArrowDown") foco = (foco + 1) % nos.length;
      else if (ev.key === "ArrowLeft" || ev.key === "ArrowUp") foco = (foco - 1 + nos.length) % nos.length;
      else if (ev.key === "Enter" && foco >= 0) { aoAbrir(nos[foco].ref); return; }
      else return;
      ev.preventDefault(); tocou(); if (reduzir.matches) desenhar(performance.now());
    });
    document.addEventListener("visibilitychange", retomar);
    window.addEventListener("resize", () => { if (aberto) { ajustar(); tocou(); desenhar(performance.now()); } });

    return {
      aoAbrir(f) { aoAbrir = f; },
      async mostrar() {  // chamado quando a aba Mapa abre: carrega os dados e liga o laço
        const dados = await window.pywebview.api.memory_graph();
        if (dados.error) return dados.error;
        aberto = true; foco = sobre = -1;
        ajustar(); posicionar(dados); desenharLegenda(dados);
        ultimaAcao = performance.now(); desenhar(ultimaAcao); retomar();
        return "";
      },
      parar() { aberto = false; rodando = false; },
    };
  })();
