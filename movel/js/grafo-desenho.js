// Desenho do grafo do Second Brain em Canvas 2D. Os textos das notas só entram por fillText (nunca por HTML).
import { AREA_POR_ID, raioDoNo } from "./areas.js";

const NUCLEO = "#00e5ff";
const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${a})`;
};
const corDo = (no) => (no.area ? AREA_POR_ID[no.area].cor : NUCLEO);
export const cortarRotulo = (t, max = 26) => (t.length > max ? t.slice(0, max - 1) + "…" : t);

// Curva suave entre dois pontos: o ponto de controle sai do meio, de lado, na direção de um sinal fixo por aresta.
export function controle(a, b, k) {
  const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2, dx = b.x - a.x, dy = b.y - a.y, lado = (k % 2 ? 1 : -1) * 0.14;
  return { x: mx - dy * lado, y: my + dx * lado };
}

export const pontoNaCurva = (a, c, b, u) => ({
  x: (1 - u) * (1 - u) * a.x + 2 * (1 - u) * u * c.x + u * u * b.x,
  y: (1 - u) * (1 - u) * a.y + 2 * (1 - u) * u * c.y + u * u * b.y,
});

// estado = { t (s), pulsos: [{aresta, u}], selecionado (id|null), animar (bool) }
export function desenharGrafo(ctx, grafo, pos, largura, altura, estado) {
  ctx.clearRect(0, 0, largura, altura);
  const t = estado.t, deriva = (no, i) => (estado.animar ? { x: Math.sin(t * 0.7 + i) * 1.8, y: Math.cos(t * 0.6 + i * 1.3) * 1.8 } : { x: 0, y: 0 });
  const lugar = new Map(grafo.nos.map((no, i) => { const p = pos.get(no.id), d = deriva(no, i); return [no.id, { x: p.x + d.x, y: p.y + d.y }]; }));
  ctx.lineCap = "round";
  grafo.arestas.forEach((e, k) => {
    const a = lugar.get(e.de), b = lugar.get(e.para), c = controle(a, b, k), cor = corDo(grafo.porId.get(e.para));
    ctx.strokeStyle = rgba(cor.startsWith("#") ? cor : NUCLEO, e.link ? 0.6 : 0.22);
    ctx.lineWidth = e.link ? 1.3 : 1;
    ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.quadraticCurveTo(c.x, c.y, b.x, b.y); ctx.stroke();
  });
  ctx.globalCompositeOperation = "lighter";
  for (const p of estado.pulsos || []) {  // pulsos de luz correndo pelas ligações
    const e = grafo.arestas[p.aresta];
    if (!e) continue;
    const a = lugar.get(e.de), b = lugar.get(e.para), q = pontoNaCurva(a, controle(a, b, p.aresta), b, p.u);
    ctx.fillStyle = rgba(corDo(grafo.porId.get(e.para)), 0.9);
    ctx.beginPath(); ctx.arc(q.x, q.y, 2.2, 0, Math.PI * 2); ctx.fill();
  }
  ctx.globalCompositeOperation = "source-over";
  for (const no of grafo.nos) {
    const p = lugar.get(no.id), cor = corDo(no);
    let r = raioDoNo(no);
    if (no.tipo === "nucleo") {  // núcleo pulsante
      r *= 1 + (estado.animar ? 0.12 * Math.sin(t * 2.2) : 0);
      const g = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, r * 2.6);
      g.addColorStop(0, rgba(NUCLEO, 0.55)); g.addColorStop(1, rgba(NUCLEO, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(p.x, p.y, r * 2.6, 0, Math.PI * 2); ctx.fill();
    }
    ctx.fillStyle = rgba(cor, no.tipo === "nota" ? 0.9 : 1);
    ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fill();
    if (estado.selecionado === no.id) { ctx.strokeStyle = "#ffffff"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2); ctx.stroke(); }
  }
  ctx.font = "12px -apple-system, system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.fillStyle = "#dff6ff";
  for (const no of grafo.nos) {  // rótulos: núcleo, áreas e a nota escolhida
    if (no.tipo === "nota" && estado.selecionado !== no.id) continue;
    const p = lugar.get(no.id);
    ctx.fillText(cortarRotulo(no.rotulo), p.x, p.y - raioDoNo(no) - 7);
  }
  return lugar;
}
