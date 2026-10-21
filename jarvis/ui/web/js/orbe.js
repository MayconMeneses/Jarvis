  // ── Orbe: o ÚNICO componente (janela principal e modo foco). Anel de filamentos em Canvas 2D (orbe-filamentos.js). ──
  // Orbe.montar(canvas): o tamanho vem do CSS (ResizeObserver, buffer refeito só quando muda); o estado vem de um lugar
  // só (Orbe.set, em orbe-estado.js). 30 fps (15 parado), pausa com a janela oculta, fora da tela ou desligado.
  // Modo "suave": sem rotação nem pulso. Máquina lenta: custo médio > 9 ms/quadro vira metade dos filamentos; > 12 ms, 20 fps.
  (() => {
    const O = window.Orbe, F = window.OrbeFil;
    if (!O || !F) return;
    const TAU = Math.PI * 2, instancias = [];
    // Alvo de cada estado: cor, brilho (a), giro (rad/s), velocidade da ondulação, amplitude, espalhamento, radar, spinner.
    const ALVO = {
      idle:      { r: 63,  g: 208, b: 255, a: 0.55, giro: 0.06, vel: 0.35, amp: 0.25, espalha: 0.09, radar: 0, spin: 0 },
      listening: { r: 63,  g: 208, b: 255, a: 0.9,  giro: 0.12, vel: 0.8,  amp: 1,    espalha: 0.1,  radar: 1, spin: 0 },
      thinking:  { r: 255, g: 154, b: 60,  a: 0.85, giro: 0.6,  vel: 1.6,  amp: 0.35, espalha: 0.06, radar: 0, spin: 1 },
      speaking:  { r: 110, g: 220, b: 255, a: 0.85,    giro: 0.14, vel: 1,    amp: 1,    espalha: 0.12, radar: 0, spin: 0 },
    };
    const CAMPOS = ["r", "g", "b", "a", "giro", "vel", "amp", "espalha", "radar", "spin"];
    const PERFIL = { completo: { N: 32, M: 88, P: 60, full: true }, suave: { N: 20, M: 48, P: 30, full: false }, leve: { N: 20, M: 56, P: 30, full: true } };
    function corDoTema() {  // espera/ouvindo seguem --cyan; processando segue --orange; falando é o --glow
      const T = window.Cores.ler(), rgb = (c) => (c.match(/\d+/g) || []).slice(0, 3).map(Number);
      const pinta = (e, v) => { if (v.length === 3) [ALVO[e].r, ALVO[e].g, ALVO[e].b] = v; };
      pinta("idle", rgb(T.cyan)); pinta("listening", rgb(T.cyan)); pinta("thinking", rgb(T.orange)); const c = rgb(T.cyan), gl = rgb(T.glow || T.text);
      pinta("speaking", c.map((v, i) => Math.round(v + ((gl[i] ?? v) - v) * 0.3)));  // falando: o ciano do tema, só mais claro (sem estourar em branco)
    }
    window.addEventListener("jarvis-tema", () => { corDoTema(); instancias.forEach((i) => i.ligar()); });
    corDoTema();

    function montar(cv) {
      if (!cv || !cv.getContext) return null;
      const ctx = cv.getContext("2d"), p = Object.assign({}, ALVO.idle);
      let L = 0, DPR = 1, ph = 0, rot = 0, giroArco = 0, leve = false, lento = 0, raf = 0, ultimo = 0, custo = 0, quadros = 0;
      let ativo = true, naTela = true, medio = 0, fpsReal = 0, contaFps = 0, t0Fps = 0;

      function medir() {
        const lado = Math.max(1, Math.round(cv.clientWidth));
        if (lado === L) return;
        L = lado; DPR = Math.min(window.devicePixelRatio || 1, lento ? 1.25 : 1.5, 1024 / L);
        cv.width = cv.height = Math.max(1, Math.round(L * DPR));
        if (O.modoEfetivo() === "desligado") estatico();
      }
      let espera = 0;
      if (window.ResizeObserver) new ResizeObserver(() => { clearTimeout(espera); espera = setTimeout(() => { medir(); ligar(); }, 120); }).observe(cv);
      if (window.IntersectionObserver) new IntersectionObserver((e) => { naTela = e[e.length - 1].isIntersecting; if (naTela) ligar(); else parar(); }).observe(cv);

      const perfil = () => (O.modoEfetivo() === "suave" ? PERFIL.suave : leve ? PERFIL.leve : PERFIL.completo);
      function desenhar(n, c) {
        const g = { C: L / 2, R: L / 2 };
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.globalCompositeOperation = "source-over"; ctx.clearRect(0, 0, L, L);
        ctx.globalCompositeOperation = "lighter";
        F.anel(ctx, g, p, n, ph, rot, giroArco, c);
        F.moldura(ctx, g, p, n, giroArco, c.full);
      }
      function quadro(dt) {
        const c = perfil(), n = O.passo(performance.now(), dt), k = 1 - Math.exp(-dt / 0.25), alvo = ALVO[O.s.estado] || ALVO.idle;
        for (const f of CAMPOS) p[f] += (alvo[f] - p[f]) * k;
        if (c.full) { ph += p.vel * dt; rot += p.giro * dt; giroArco += (0.05 + p.spin * 3.2) * dt; }
        desenhar(n, c);
      }
      function estatico() {  // modo desligado: um quadro parado, sem animação
        if (!L) medir();
        Object.assign(p, ALVO[O.s.estado] || ALVO.idle);
        desenhar(0, { N: 20, M: 48, P: 0, full: false });
      }

      function ciclo(ts) {
        raf = 0;
        if (document.hidden || !ativo || !naTela) return;
        const modo = O.modoEfetivo();
        if (modo === "desligado") { estatico(); return; }
        const parado = O.s.estado === "idle" && O.s.nivel < 0.02;
        let fps = modo === "suave" ? (parado ? 8 : 20) : parado ? 15 : 30;
        if (lento) fps = Math.min(fps, 20);
        const min = 1000 / fps;
        if (ts - ultimo >= min - 3) {
          const dt = Math.min(0.1, (ts - ultimo) / 1000 || min / 1000);
          ultimo = ts;
          const t0 = performance.now(); quadro(dt); custo += performance.now() - t0;
          contaFps++;
          if (++quadros === 60) {
            medio = custo / quadros;
            if (medio > 9 && !leve) leve = true; else if (medio > 12) lento = 1;
            fpsReal = contaFps / ((ts - t0Fps) / 1000 || 1); contaFps = 0; t0Fps = ts;
            custo = 0; quadros = 0;
          }
        }
        raf = requestAnimationFrame(ciclo);
      }
      function ligar() { if (ativo && naTela && !raf && !document.hidden) { medir(); ultimo = 0; t0Fps = performance.now(); contaFps = 0; raf = requestAnimationFrame(ciclo); } }
      function parar() { if (raf) { cancelAnimationFrame(raf); raf = 0; } }
      function ativar(sim) { ativo = !!sim; if (ativo) ligar(); else parar(); }
      const debug = () => ({ rodando: !!raf, ativo, lado: L, dpr: DPR, filamentos: perfil().N, pontosPorFio: perfil().M, leve, lento: !!lento,
        custoMsPorQuadro: +medio.toFixed(2), fpsReal: +fpsReal.toFixed(1), estado: O.s.estado, nivel: O.s.nivel, modo: O.modoEfetivo() });

      document.addEventListener("visibilitychange", () => { if (document.hidden) parar(); else ligar(); });
      O.aoMudar(ligar);
      const ctl = { ligar, parar, ativar, debug };
      instancias.push(ctl);
      ligar();
      return ctl;
    }

    O.montar = montar;
    O.principal = montar(document.getElementById("orbe"));
    window.__orbeDebug = () => (O.principal ? O.principal.debug() : {});
  })();
