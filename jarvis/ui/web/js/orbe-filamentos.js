  // ── Orbe: desenho do anel de FILAMENTOS (Canvas 2D, sem biblioteca, sem sombra de canvas, sem alocar por quadro) ──
  // Cada filamento é uma polilinha fechada sobre uma elipse perturbada por 3 senos (ondulações inteiras por volta:
  // o laço fecha). Composição "lighter" (a luz soma). Os fios são agrupados em 4 faixas de alfa: um traçado por faixa
  // e por passe (halo largo + fio fino). Pontos de luz vêm de um sprite pré-renderizado (sem gradiente por quadro).
  // Só desenha: o estado e o nível de voz vêm de orbe-estado.js; o laço de quadros fica em orbe.js.
  window.OrbeFil = (() => {
    const TAU = Math.PI * 2, OURO = 2.399963, NMAX = 40, MMAX = 96, FAIXAS = 4;
    const PX = new Float32Array(NMAX * (MMAX + 1)), PY = new Float32Array(NMAX * (MMAX + 1));
    const COS = new Float32Array(MMAX + 1), SEN = new Float32Array(MMAX + 1);
    const W1 = new Uint8Array(NMAX), W2 = new Uint8Array(NMAX), FASE = new Float32Array(NMAX), AMPF = new Float32Array(NMAX), BALDE = new Uint8Array(NMAX);
    for (let f = 0; f < NMAX; f++) { W1[f] = 3 + (f % 3); W2[f] = 6 + (f % 3); FASE[f] = f * OURO; AMPF[f] = 0.4 + 1.5 * ((f * 0.618) % 1); }  // cada fio passeia mais ou menos: os fios se cruzam
    let mTabela = 0, spriteCv = null, spriteChave = "";

    function tabela(M) {
      if (mTabela === M) return;
      for (let j = 0; j <= M; j++) { const th = (j / M) * TAU; COS[j] = Math.cos(th); SEN[j] = Math.sin(th); }
      mTabela = M;
    }
    // Sprite radial branco-azulado, refeito só quando a cor muda de verdade (passos de 16 por canal).
    function sprite(r, g, b) {
      const chave = (r >> 4) + "," + (g >> 4) + "," + (b >> 4);
      if (spriteCv && chave === spriteChave) return spriteCv;
      if (!spriteCv) { spriteCv = document.createElement("canvas"); spriteCv.width = spriteCv.height = 48; }
      const c = spriteCv.getContext("2d"), gr = c.createRadialGradient(24, 24, 0, 24, 24, 24);
      const cl = (v) => Math.round(v + (255 - v) * 0.7);  // centro do ponto: a cor do estado bem clareada
      gr.addColorStop(0, `rgba(${cl(r)},${cl(g)},${cl(b)},1)`); gr.addColorStop(0.25, `rgba(${r},${g},${b},.75)`); gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
      c.clearRect(0, 0, 48, 48); c.fillStyle = gr; c.fillRect(0, 0, 48, 48);
      spriteChave = chave;
      return spriteCv;
    }
    const lim = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);

    // Desloca um raio pela soma de senos do filamento f no ângulo th (ph = fase integrada do movimento).
    const onda = (f, th, ph) => 0.58 * Math.sin(W1[f] * th + FASE[f] + ph * 1.3) + 0.32 * Math.sin(W2[f] * th - FASE[f] * 0.7 - ph * 1.9) + 0.1 * Math.sin(9 * th + ph * 0.7);

    // g: {C, R} em px CSS; p: estado suavizado {r,g,b,a,vel,amp,espalha,spin,radar}; n: nível 0..1; c: {N, M, P, full}
    function anel(ctx, g, p, n, ph, rot, giroArco, c) {
      const N = Math.min(NMAX, c.N), M = Math.min(MMAX, c.M), esc = Math.max(0.7, g.R / 200);
      tabela(M);
      const R0 = g.R * 0.66 * (c.full ? 1 + 0.03 * Math.sin(ph * 0.5) + 0.05 * n : 1);
      const A = R0 * (0.075 + p.amp * (0.04 + 0.085 * n)), elip = c.full ? 0.94 + 0.04 * Math.sin(ph * 0.3) : 0.97;
      const vivo = (0.7 + 0.5 * n) * p.a;
      for (let f = 0; f < N; f++) {
        const u = N > 1 ? f / (N - 1) - 0.5 : 0, Rf = R0 * (1 + p.espalha * u * 2), ang = rot + 0.15 * u, cr = Math.cos(ang), sr = Math.sin(ang);
        BALDE[f] = Math.min(FAIXAS - 1, ((1 - Math.abs(2 * u)) * FAIXAS) | 0);
        const base = f * (MMAX + 1);
        for (let j = 0; j <= M; j++) {
          const r = Rf + A * AMPF[f] * onda(f, (j / M) * TAU, ph), x = r * COS[j], y = r * SEN[j] * elip;
          PX[base + j] = g.C + x * cr - y * sr; PY[base + j] = g.C + x * sr + y * cr;
        }
      }
      ctx.lineJoin = "round"; ctx.lineCap = "round";
      for (let b = 0; b < FAIXAS; b++) {
        const alfa = lim(vivo * (0.2 + 0.1 * b));
        ctx.beginPath();
        for (let f = 0; f < N; f++) {
          if (BALDE[f] !== b) continue;
          const base = f * (MMAX + 1);
          ctx.moveTo(PX[base], PY[base]);
          for (let j = 1; j <= M; j++) ctx.lineTo(PX[base + j], PY[base + j]);
        }
        ctx.lineWidth = 3 * esc; ctx.strokeStyle = `rgba(${p.r | 0},${p.g | 0},${p.b | 0},${alfa * 0.2})`; ctx.stroke();  // halo
        ctx.lineWidth = Math.max(0.8, 1.05 * esc); ctx.strokeStyle = `rgba(${p.r | 0},${p.g | 0},${p.b | 0},${lim(alfa * 0.95)})`; ctx.stroke();  // fio
      }
      // Pontos de luz: nós de energia andando pelos filamentos; 1 em 7 pisca mais forte com a voz.
      if (c.P > 0) {
        const sp = sprite(p.r | 0, p.g | 0, p.b | 0);
        for (let q = 0; q < c.P; q++) {
          const f = q % N, u = N > 1 ? f / (N - 1) - 0.5 : 0, th = (q / c.P) * TAU + ph * 0.45 * (1 + 0.6 * Math.sin(q));
          const r = R0 * (1 + p.espalha * u * 2) + A * AMPF[f] * onda(f, th, ph), ang = rot + 0.15 * u;
          const x = r * Math.cos(th), y = r * Math.sin(th) * elip, tam = (5 + (q % 7 === 0 ? 11 * n : 2)) * esc;
          ctx.globalAlpha = lim(p.a * (0.35 + 0.45 * Math.sin(ph * 1.4 + q * 1.7) ** 2) + (q % 7 === 0 ? 0.4 * n : 0));
          ctx.drawImage(sp, g.C + x * Math.cos(ang) - y * Math.sin(ang) - tam, g.C + x * Math.sin(ang) + y * Math.cos(ang) - tam, tam * 2, tam * 2);
        }
        ctx.globalAlpha = 1;
        const nuc = g.R * (0.7 + 0.25 * n);  // clarão suave no miolo (o cartão do briefing fica por cima)
        ctx.globalAlpha = lim(0.07 + 0.2 * n) * p.a; ctx.drawImage(sp, g.C - nuc, g.C - nuc, nuc * 2, nuc * 2); ctx.globalAlpha = 1;
      }
    }

    function cor(p, a) { return `rgba(${p.r | 0},${p.g | 0},${p.b | 0},${lim(a)})`; }
    function arco(ctx, g, p, raio, ini, tam, a, larg) {
      ctx.beginPath(); ctx.arc(g.C, g.C, raio, ini, ini + tam);
      ctx.strokeStyle = cor(p, a); ctx.lineWidth = larg; ctx.lineCap = "round"; ctx.stroke();
    }
    // Moldura: aro fino, 72 marcas (um traçado só) e, conforme o estado, radar (ouvindo) ou arcos giratórios (processando).
    function moldura(ctx, g, p, n, giroArco, full) {
      const C = g.C, R = g.R, esc = Math.max(0.7, R / 200);
      ctx.beginPath(); ctx.arc(C, C, R * 0.93, 0, TAU); ctx.strokeStyle = cor(p, 0.16 * p.a + 0.1); ctx.lineWidth = esc; ctx.stroke();
      ctx.beginPath();
      for (let k = 0; k < 72; k++) {
        const th = (k / 72) * TAU + (full ? giroArco * 0.04 : 0), r1 = R * (k % 6 ? 0.9 : 0.87), r2 = R * 0.93;
        ctx.moveTo(C + r1 * Math.cos(th), C + r1 * Math.sin(th)); ctx.lineTo(C + r2 * Math.cos(th), C + r2 * Math.sin(th));
      }
      ctx.strokeStyle = cor(p, 0.28 * p.a + 0.06); ctx.lineWidth = esc; ctx.stroke();
      if (p.spin > 0.05) for (let k = 0; k < 3; k++) arco(ctx, g, p, R * 0.84, (full ? giroArco : -1) + (k * TAU) / 3, 0.7, 0.8 * p.spin, 2.2 * esc);
      if (p.radar > 0.05) for (let k = 0; k < 3; k++) arco(ctx, g, p, R * 0.84 * (1 - 0.05 * n), (k * TAU) / 3 - 0.5, 0.9, 0.55 * p.radar, 2 * esc);
    }
    return { anel, moldura, NMAX, MMAX };
  })();
