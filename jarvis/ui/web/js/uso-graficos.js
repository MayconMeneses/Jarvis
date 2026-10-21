  // ── Uso de IA: gráficos em canvas próprio (sem biblioteca externa) ───────
  const UsoGraficos = (() => {
    const cor = (i) => window.Cores.serie(i);

    function preparar(canvas) {
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth || 300, h = canvas.clientHeight || 170;
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      return { ctx, w, h };
    }

    function barras(canvas, dias) {
      const { ctx, w, h } = preparar(canvas);
      const base = h - 18, topo = 8, esq = 38;
      const max = Math.max(...dias.map((d) => d.custo), 0.01);
      const T = window.Cores.ler();
      ctx.font = "10px Consolas, monospace"; ctx.fillStyle = T.muted; ctx.strokeStyle = window.Cores.alfa(T.cyan, 0.18);
      for (let i = 0; i <= 2; i++) {
        const y = base - ((base - topo) * i) / 2;
        ctx.beginPath(); ctx.moveTo(esq, y); ctx.lineTo(w, y); ctx.stroke();
        ctx.textAlign = "right"; ctx.fillText("$" + ((max * i) / 2).toLocaleString("pt-BR", { minimumFractionDigits: max < 10 ? 2 : 0, maximumFractionDigits: max < 10 ? 2 : 0 }), esq - 4, y + 3);
      }
      if (!dias.length) return;
      const largura = (w - esq) / dias.length;
      dias.forEach((d, i) => {
        const alto = ((base - topo) * d.custo) / max;
        ctx.fillStyle = cor(0);
        ctx.fillRect(esq + i * largura + largura * 0.15, base - alto, Math.max(largura * 0.7, 1), alto);
      });
      ctx.fillStyle = T.muted; ctx.textAlign = "left"; ctx.fillText(dias[0].dia.slice(5), esq, h - 4);
      ctx.textAlign = "right"; ctx.fillText(dias[dias.length - 1].dia.slice(5), w, h - 4);
    }

    function rosca(canvas, itens) {
      const { ctx, w, h } = preparar(canvas);
      const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 6;
      const total = itens.reduce((s, i) => s + i.valor, 0);
      if (!total) { ctx.strokeStyle = window.Cores.alfa(window.Cores.ler().cyan, 0.3); ctx.beginPath(); ctx.arc(cx, cy, r, 0, 7); ctx.stroke(); return; }
      let ang = -Math.PI / 2;
      itens.forEach((it, i) => {
        const fim = ang + (it.valor / total) * Math.PI * 2;
        ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, r, ang, fim); ctx.closePath();
        ctx.fillStyle = cor(i); ctx.fill();
        ang = fim;
      });
      ctx.globalCompositeOperation = "destination-out";
      ctx.beginPath(); ctx.arc(cx, cy, r * 0.58, 0, Math.PI * 2); ctx.fill();
      ctx.globalCompositeOperation = "source-over";
    }

    return { barras, rosca, cor };
  })();
  window.UsoGraficos = UsoGraficos;
