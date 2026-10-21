  // ── Ondas de áudio laterais e orbe pequeno de escuta (embaixo do orbe grande) ─────────────────────────────────
  // Tudo em Canvas 2D, lendo o nível REAL que já alimenta o Orbe (window.onVoice: tipos "mic" e "fala").
  // Painel ENTRADA = volume do microfone (só enquanto ouve); painel SAÍDA = nível da fala (só enquanto fala). Parado = linha reta.
  // Histórico de 60 amostras a ~20 Hz (3 s). Laço único a <= 20 fps: parado com a janela oculta, efeitos desligados,
  // canvases fora da tela ou nada acontecendo (espera com histórico já zerado). Sem biblioteca e sem alocar por quadro.
  const OndasRegras = (() => {
    const N = 60;
    // Valor de cada canal a partir do estado do Orbe: {estado, mic, micT, nivel} + "agora" (ms).
    function canais(s, agora) {
      return { entrada: s.estado === "listening" && agora - s.micT < 500 ? s.mic : 0, saida: s.estado === "speaking" ? s.nivel : 0 };
    }
    // Anel de amostras: a cabeça aponta para a próxima posição a escrever. Devolve a nova cabeça.
    function empurrar(buf, cabeca, v) { buf[cabeca] = Math.max(0, Math.min(1, Number(v) || 0)); return (cabeca + 1) % buf.length; }
    // Amostra i do anel (0 = a mais nova).
    const amostra = (buf, cabeca, i) => buf[(cabeca - 1 - i + buf.length * 2) % buf.length];
    const zerado = (buf) => { for (let i = 0; i < buf.length; i++) if (buf[i] > 0.01) return false; return true; };
    // Textura da forma de onda: o nível manda; a alternância só dá aspecto de sinal (silêncio continua reto).
    const forma = (i) => 0.72 + 0.28 * Math.sin(i * 2.3) * Math.cos(i * 0.9);
    return { N, canais, empurrar, amostra, zerado, forma };
  })();
  if (typeof module !== "undefined") module.exports = OndasRegras;

  if (typeof window !== "undefined" && typeof document !== "undefined" && window.Orbe) window.Ondas = (() => {
    const O = window.Orbe, R = OndasRegras, N = R.N, TAU = Math.PI * 2, C = window.Cores;
    const ent = new Float32Array(N), sai = new Float32Array(N);
    let cabeca = 0, raf = 0, ultimo = 0, tAmostra = 0, ocupado = false, disponivel = true, custo = 0, quadros = 0;
    const painel = [], vistos = new Set(), botao = document.getElementById("escuta");
    const anelCv = document.getElementById("escuta-anel"), anelCtx = anelCv ? anelCv.getContext("2d") : null;
    const alvoAnel = anelCv ? { cv: anelCv, L: 0, A: 0, dpr: 1, dprMax: Math.min(window.devicePixelRatio || 1, 2) } : null;
    for (const [id, buf] of [["onda-entrada", ent], ["onda-saida", sai]]) {
      const cv = document.getElementById(id);
      if (cv) painel.push({ cv, buf, ctx: cv.getContext("2d"), L: 0, A: 0, dpr: 1, dprMax: 1 });  // traço fino num painel estreito: 1x basta
    }

    // Strings de cor prontas (refeitas só quando o tema muda): nada de regex nem de alocação a cada quadro.
    let K = null;
    const cores = () => {
      if (K) return K;
      const T = C.ler(), par = (c) => ({ fio: C.alfa(c, 0.9), massa: C.alfa(c, 0.22), halo: C.alfa(c, 0.25), aro: C.alfa(c, 0.6), aroVivo: C.alfa(c, 0.95), fino: C.alfa(c, 0.45) });
      K = { cyan: par(T.cyan), glow: par(T.glow), orange: par(T.orange), miolo: C.alfa(T.glow, 0.95) };
      return K;
    };
    window.addEventListener("jarvis-tema", () => { K = null; });

    // Tamanho: lido só quando o canvas muda de tamanho (ResizeObserver), nunca a cada quadro (evitava reflow forçado).
    function dimensionar(p, l, a) {
      l = Math.round(l); a = Math.round(a);
      if (l === p.L && a === p.A) return;
      p.L = l; p.A = a; p.plano = false;
      p.dpr = p.dprMax || 1; p.cv.width = Math.max(1, Math.round(l * p.dpr)); p.cv.height = Math.max(1, Math.round(a * p.dpr));
    }
    const medir = (p) => {
      if (!p.L && !window.ResizeObserver) dimensionar(p, p.cv.clientWidth, p.cv.clientHeight);  // sem RO (navegador antigo): lê uma vez
      return p.L > 0 && p.A > 0;
    };
    // Forma de onda vertical simétrica: o tempo desce (amostra nova no topo) e a amplitude abre para os dois lados.
    // Canal em silêncio e já desenhado reto: não redesenha (metade do tempo um dos dois painéis está parado).
    function onda(p, k) {
      if (!medir(p)) return;
      const silencio = R.zerado(p.buf);
      if (silencio && p.plano && p.k === k) return;
      const c = p.ctx, L = p.L, A = p.A, meio = L / 2, max = L / 2 - 3, passo = (A - 4) / (N - 1);
      c.setTransform(p.dpr, 0, 0, p.dpr, 0, 0); c.clearRect(0, 0, L, A);
      c.beginPath();
      if (silencio) { c.moveTo(meio, 2); c.lineTo(meio, A - 2); } else {
        for (let i = 0; i < N; i += 2) c.lineTo(meio + R.amostra(p.buf, cabeca, i) * R.forma(i) * max, 2 + i * passo);  // 30 pontos por lado bastam num painel de 64 px
        for (let i = N - 2; i >= 0; i -= 2) c.lineTo(meio - R.amostra(p.buf, cabeca, i) * R.forma(i) * max, 2 + i * passo);
        c.closePath(); c.fillStyle = k.massa; c.fill();
      }
      c.lineWidth = 1.2; c.strokeStyle = k.fio; c.stroke();
      p.plano = silencio; p.k = k;
    }
    // Orbe pequeno: miolo claro + anel que abre com o nível; processando = arco giratório (cor laranja do tema).
    // Só círculos cheios e traços (sem gradiente por quadro).
    function anel(agora) {
      if (!anelCtx || !medir(alvoAnel)) return;
      const L = alvoAnel.L, K2 = cores(), est = O.s.estado, c = anelCtx, dpr = alvoAnel.dpr;
      const m = L / 2, n = est === "listening" ? Math.max(O.s.nivel, 0.06) : O.s.nivel, k = est === "thinking" ? K2.orange : K2.cyan;
      c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, L, L);
      c.fillStyle = k.halo; c.beginPath(); c.arc(m, m, m * (0.5 + 0.32 * n), 0, TAU); c.fill();
      c.fillStyle = K2.miolo; c.beginPath(); c.arc(m, m, m * (0.16 + 0.1 * n), 0, TAU); c.fill();
      c.lineWidth = 1.5; c.strokeStyle = est === "idle" ? k.aro : k.aroVivo; c.beginPath(); c.arc(m, m, m * (0.7 + 0.2 * n), 0, TAU); c.stroke();
      c.lineWidth = 1.2; c.strokeStyle = k.fino; c.beginPath();
      if (est === "thinking") c.arc(m, m, m * 0.92, agora / 380, agora / 380 + 1.6); else c.arc(m, m, m * 0.92, 0, TAU);
      c.stroke();
    }
    const visivel = () => painel.some((p) => vistos.has(p.cv)) || (!!anelCv && vistos.has(anelCv));

    function quadro(agora) {
      if (O.principal && !O.principal.roda()) O.passo(agora, 0.05);  // orbe grande parado (fora da tela): o nível é atualizado aqui
      if (agora - tAmostra >= 48) {
        const v = R.canais(O.s, agora); tAmostra = agora;
        R.empurrar(sai, cabeca, v.saida); cabeca = R.empurrar(ent, cabeca, v.entrada);
        ocupado = O.s.estado !== "idle" || !R.zerado(ent) || !R.zerado(sai);
      }
      const K2 = cores();
      if (painel[0]) onda(painel[0], K2.cyan);
      if (painel[1]) onda(painel[1], O.s.estado === "speaking" ? K2.glow : K2.cyan);
      anel(agora);
    }
    function estatico() { ent.fill(0); sai.fill(0); painel.forEach((p) => onda(p, cores().cyan)); anel(0); }
    function ciclo(ts) {
      raf = 0;
      if (document.hidden || !visivel()) return;
      if (O.modoEfetivo() === "desligado") { estatico(); return; }
      if (ts - ultimo >= 48) { ultimo = ts; const t0 = performance.now(); quadro(t0); custo += performance.now() - t0; quadros++; }
      if (ocupado) raf = requestAnimationFrame(ciclo);  // histórico zerado e em espera: nada a animar, o laço dorme
    }
    function ligar() { if (!raf && !document.hidden && disponivel) { ocupado = true; raf = requestAnimationFrame(ciclo); } }

    if (window.ResizeObserver) {
      const ro = new ResizeObserver((es) => es.forEach((e) => {
        const p = painel.find((x) => x.cv === e.target) || (alvoAnel && alvoAnel.cv === e.target ? alvoAnel : null);
        if (p) { dimensionar(p, e.contentRect.width, e.contentRect.height); ligar(); }
      }));
      painel.forEach((p) => ro.observe(p.cv)); if (anelCv) ro.observe(anelCv);
    }
    if (window.IntersectionObserver) {
      const io = new IntersectionObserver((es) => { es.forEach((e) => (e.isIntersecting ? vistos.add(e.target) : vistos.delete(e.target))); ligar(); });
      painel.forEach((p) => io.observe(p.cv)); if (anelCv) io.observe(anelCv);
    } else { painel.forEach((p) => vistos.add(p.cv)); if (anelCv) vistos.add(anelCv); }
    document.addEventListener("visibilitychange", ligar);
    window.addEventListener("jarvis-tema", ligar);
    O.aoMudar(() => {
      if (botao) { botao.setAttribute("aria-pressed", O.s.estado === "listening" ? "true" : "false"); botao.dataset.estado = O.s.estado; }
      ligar();
    });
    if (botao) botao.addEventListener("click", () => { try { window.pywebview.api.listen_now(); } catch (e) { /* fora da janela */ } });
    // Sem voz neste PC, o botão some (a conversa por texto continua igual).
    function definirDisponivel(sim) {
      disponivel = !!sim; const linha = document.getElementById("escuta-linha");
      if (linha) linha.hidden = !disponivel;
      if (disponivel) ligar();
    }
    ligar();
    return { definirDisponivel, debug: () => ({ custoMsPorQuadro: quadros ? +(custo / quadros).toFixed(2) : 0, quadros, rodando: !!raf, visiveis: vistos.size, ocupado, ent: Array.from(ent), sai: Array.from(sai) }) };
  })();
