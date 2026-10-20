  // ── Orbe: desenho em Canvas 2D (sem biblioteca, sem shadowBlur) ──────
  // Núcleo com anéis, onda circular e ~120 pontos numa esfera girando. 30 fps (15 parado), DPR até 2,
  // pausa com a janela oculta. Modo "suave": sem rotação nem pulso de escala, só brilho/opacidade.
  (() => {
    const cv = document.getElementById("orbe");
    if (!cv || !cv.getContext) return;
    const ctx = cv.getContext("2d");
    const O = window.Orbe;
    const L = 148, C = L / 2, DPR = Math.min(window.devicePixelRatio || 1, 2), TAU = Math.PI * 2;
    cv.width = cv.height = Math.round(L * DPR);
    const NMAX = 120, PONTOS = new Float32Array(NMAX * 3);
    for (let i = 0; i < NMAX; i++) {  // esfera de Fibonacci
      const y = 1 - (2 * (i + 0.5)) / NMAX, r = Math.sqrt(1 - y * y), th = i * 2.399963;
      PONTOS[i * 3] = Math.cos(th) * r; PONTOS[i * 3 + 1] = y; PONTOS[i * 3 + 2] = Math.sin(th) * r;
    }
    // Alvo de cada estado: cor, intensidade, giro (rad/s), força da onda, radar (ouvindo), spinner (pensando).
    const ALVO = {
      idle:      { r: 63,  g: 208, b: 255, a: 0.38, giro: 0.06, onda: 0.15, radar: 0, spin: 0 },
      listening: { r: 63,  g: 208, b: 255, a: 0.9,  giro: 0.12, onda: 1,    radar: 1, spin: 0 },
      thinking:  { r: 255, g: 154, b: 60,  a: 0.85, giro: 0.6,  onda: 0.2,  radar: 0, spin: 1 },
      speaking:  { r: 175, g: 240, b: 255, a: 1,    giro: 0.14, onda: 1,    radar: 0, spin: 0 },
    };
    const p = Object.assign({}, ALVO.idle);
    let rot = 0, giroArco = 0, npts = NMAX, raf = 0, ultimo = 0, custo = 0, quadros = 0;

    const cor = (a) => `rgba(${p.r | 0},${p.g | 0},${p.b | 0},${Math.max(0, Math.min(1, a))})`;
    function anel(raio, a, largura) {
      ctx.beginPath(); ctx.arc(C, C, raio, 0, TAU);
      ctx.strokeStyle = cor(a); ctx.lineWidth = largura || 1; ctx.stroke();
    }
    function arco(raio, inicio, tamanho, a, largura) {
      ctx.beginPath(); ctx.arc(C, C, raio, inicio, inicio + tamanho);
      ctx.strokeStyle = cor(a); ctx.lineWidth = largura; ctx.lineCap = "round"; ctx.stroke();
    }
    function ruido(th, t) {  // soma de senos: barato e suave
      return 0.5 * Math.sin(3 * th + t * 1.7) + 0.3 * Math.sin(7 * th - t * 2.3) + 0.2 * Math.sin(11 * th + t * 0.9);
    }

    function nucleo(R0, n, full) {
      const g = ctx.createRadialGradient(C, C, 0, C, C, R0 * 2.4);
      g.addColorStop(0, `rgba(235,252,255,${0.95 * p.a})`);
      g.addColorStop(0.35, cor(0.55 * p.a + 0.2 * n));
      g.addColorStop(1, cor(0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(C, C, R0 * 2.4, 0, TAU); ctx.fill();
      anel(R0 * 1.25, 0.7 * p.a, 1.5);
      anel(R0 * 1.6, 0.3 * p.a + 0.3 * n, 1);
      if (full) for (let k = 0; k < 3; k++) arco(R0 * 1.95, giroArco * 0.8 + (k * TAU) / 3, 0.9, 0.45 * p.a, 1.5);
    }

    function onda(n, t, full) {
      const base = C * 0.76, amp = C * 0.1 * n * p.onda;
      ctx.beginPath();
      if (!full) { ctx.arc(C, C, base, 0, TAU); } else {
        for (let i = 0; i <= 96; i++) {
          const th = (i / 96) * TAU, r = base + amp * ruido(th, t);
          if (i === 0) ctx.moveTo(C + r * Math.cos(th), C + r * Math.sin(th)); else ctx.lineTo(C + r * Math.cos(th), C + r * Math.sin(th));
        }
      }
      ctx.strokeStyle = cor((full ? 0.25 : 0.12) * p.a + 0.55 * n * p.onda); ctx.lineWidth = 1.2; ctx.stroke();
    }

    function esfera(n) {
      const raio = C * 0.56 * (1 + 0.18 * n * p.onda), cy = Math.cos(rot), sy = Math.sin(rot), tilt = 0.35;
      const ct = Math.cos(tilt), st = Math.sin(tilt);
      for (let i = 0; i < npts; i++) {
        const x0 = PONTOS[i * 3], y0 = PONTOS[i * 3 + 1], z0 = PONTOS[i * 3 + 2];
        const x1 = x0 * cy + z0 * sy, z1 = -x0 * sy + z0 * cy;  // gira em Y
        const y2 = y0 * ct - z1 * st, z2 = y0 * st + z1 * ct;  // inclina em X
        const f = 1 / (1 - z2 * 0.3), prof = (z2 + 1) / 2;
        const a = (0.12 + 0.75 * prof) * p.a * (0.6 + 0.4 * n + (prof > 0.7 ? 0.3 * n : 0));
        ctx.fillStyle = cor(a);
        ctx.beginPath(); ctx.arc(C + x1 * raio * f, C + y2 * raio * f, 0.6 + 1.3 * prof, 0, TAU); ctx.fill();
      }
    }

    function quadro(agora, dt) {
      const modo = O.modoEfetivo(), full = modo === "completo", est = O.s.estado, alvo = ALVO[est] || ALVO.idle;
      const n = O.passo(agora, dt), k = 1 - Math.exp(-dt / 0.25);
      for (const c of ["r", "g", "b", "a", "giro", "onda", "radar", "spin"]) p[c] += (alvo[c] - p[c]) * k;
      if (full) { rot += p.giro * dt; giroArco += (0.05 + p.spin * 3.2) * dt; }
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
      ctx.globalCompositeOperation = "source-over"; ctx.clearRect(0, 0, L, L);
      ctx.globalCompositeOperation = "lighter";
      const resp = full ? 1 + 0.03 * Math.sin((agora / 4000) * TAU) : 1;
      const R0 = C * 0.22 * resp * (full ? 1 + 0.06 * n : 1);
      if (full) esfera(n);
      onda(n, agora / 1000, full);
      nucleo(R0, n, full);
      if (p.spin > 0.05) arco(C * 0.66, full ? giroArco : -1, 1.7, 0.8 * p.spin * (full ? 1 : 0.5 + 0.5 * Math.sin(agora / 300)), 2.2);
      if (p.radar > 0.05) for (let i = 0; i < 3; i++) arco(C * 0.66 * (1 - 0.06 * n), (i * TAU) / 3 - 0.5, 1, 0.7 * p.radar, 2);
    }

    function estatico() {  // modo desligado: um quadro parado, sem animação
      Object.assign(p, ALVO[O.s.estado] || ALVO.idle);
      ctx.setTransform(DPR, 0, 0, DPR, 0, 0); ctx.clearRect(0, 0, L, L);
      ctx.globalCompositeOperation = "lighter";
      p.a = 0.6; nucleo(C * 0.22, 0, false); anel(C * 0.76, 0.2, 1);
    }

    function ciclo(ts) {
      raf = 0;
      if (document.hidden) return;
      const modo = O.modoEfetivo();
      if (modo === "desligado") { estatico(); return; }
      const parado = O.s.estado === "idle" && O.s.nivel < 0.02;
      const fps = modo === "suave" ? (parado ? 8 : 20) : parado ? 15 : 30, min = 1000 / fps;
      if (ts - ultimo >= min - 3) {
        const dt = Math.min(0.1, (ts - ultimo) / 1000 || min / 1000);
        ultimo = ts;
        const t0 = performance.now(); quadro(ts, dt); custo += performance.now() - t0;
        if (++quadros === 60) {  // máquina lenta: menos pontos
          if (custo / quadros > 9 && npts > 60) npts = 60;
          custo = 0; quadros = 0;
        }
      }
      raf = requestAnimationFrame(ciclo);
    }
    function ligar() { if (!raf && !document.hidden) { ultimo = 0; raf = requestAnimationFrame(ciclo); } }
    function parar() { if (raf) { cancelAnimationFrame(raf); raf = 0; } }

    document.addEventListener("visibilitychange", () => { if (document.hidden) parar(); else ligar(); });
    O.aoMudar(ligar);
    window.__orbeDebug = () => ({ rodando: !!raf, npts, estado: O.s.estado, nivel: O.s.nivel, modo: O.modoEfetivo() });
    ligar();
  })();
