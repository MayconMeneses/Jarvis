// Gráfico de barras do custo diário em canvas próprio (sem biblioteca). A parte de contas é pura e testada; o desenho só lê as cores do tema.
export function barras(serie, largura, altura, margem = 18) {
  const maximo = Math.max(...serie.map((d) => d.custo), 1e-9), util = altura - margem, passo = largura / Math.max(1, serie.length);
  return serie.map((d, i) => {
    const h = d.custo > 0 ? Math.max(2, (d.custo / maximo) * (util - 4)) : 0;
    return { x: i * passo + passo * 0.15, y: util - h, w: passo * 0.7, h, dia: d.dia, custo: d.custo };
  });
}

export function desenharGrafico(canvas, serie) {
  const ctx = canvas.getContext?.("2d");
  if (!ctx) return;
  const r = canvas.getBoundingClientRect(), dpr = Math.min(2, window.devicePixelRatio || 1), l = r.width || 300, a = r.height || 140;
  canvas.width = Math.round(l * dpr); canvas.height = Math.round(a * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  const css = getComputedStyle(document.documentElement), cor = (n) => css.getPropertyValue(n).trim() || "#888";
  ctx.clearRect(0, 0, l, a);
  ctx.fillStyle = cor("--ciano");
  for (const b of barras(serie, l, a)) if (b.h) ctx.fillRect(b.x, b.y, b.w, b.h);
  ctx.strokeStyle = cor("--linha"); ctx.beginPath(); ctx.moveTo(0, a - 17.5); ctx.lineTo(l, a - 17.5); ctx.stroke();
  ctx.fillStyle = cor("--suave"); ctx.font = "11px sans-serif";
  ctx.fillText(serie[0]?.dia.slice(5) || "", 2, a - 4);
  ctx.textAlign = "right"; ctx.fillText(serie.at(-1)?.dia.slice(5) || "", l - 2, a - 4);
}
