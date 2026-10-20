// Desenho do orbe em Canvas 2D (sem biblioteca, sem sombra cara): núcleo, anéis, onda externa, esfera de pontos e arcos de estado.
// Tudo em pixels CSS; quem chama já aplicou a escala do devicePixelRatio. O brilho vem da composição "lighter".
const PONTOS = 48;
const ESFERA = Array.from({ length: PONTOS }, (_, i) => {  // pontos de Fibonacci numa esfera unitária
  const y = 1 - (2 * (i + 0.5)) / PONTOS, r = Math.sqrt(1 - y * y), a = i * 2.399963;
  return [Math.cos(a) * r, y, Math.sin(a) * r];
});

export const PRESETS = {
  ocioso: { cor: [0, 229, 255], alfa: 0.35, giro: 0.08, spin: 0, radar: 0 },
  ouvindo: { cor: [0, 229, 255], alfa: 0.9, giro: 0.2, spin: 0, radar: 1 },
  pensando: { cor: [255, 154, 60], alfa: 0.8, giro: 0.6, spin: 1, radar: 0 },
  falando: { cor: [200, 250, 255], alfa: 1, giro: 0.3, spin: 0, radar: 0 },
};

const rgba = (c, a) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${Math.max(0, Math.min(1, a)).toFixed(3)})`;
const ruido = (a, t) => 0.5 * Math.sin(a * 3 + t * 2.1) + 0.3 * Math.sin(a * 5 - t * 1.3) + 0.2 * Math.sin(a * 8 + t * 0.7);

function nucleo(ctx, cx, cy, raio, p) {
  const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, raio * 1.6);
  g.addColorStop(0, rgba([255, 255, 255], p.alfa * 0.9));
  g.addColorStop(0.45, rgba(p.cor, p.alfa * 0.7));
  g.addColorStop(1, rgba(p.cor, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(cx, cy, raio * 1.6, 0, Math.PI * 2);
  ctx.fill();
}

function anel(ctx, cx, cy, raio, cor, largura) {
  ctx.strokeStyle = cor;
  ctx.lineWidth = largura;
  ctx.beginPath();
  ctx.arc(cx, cy, raio, 0, Math.PI * 2);
  ctx.stroke();
}

function onda(ctx, cx, cy, raio, amp, p) {
  ctx.strokeStyle = rgba(p.cor, p.alfa * 0.55);
  ctx.lineWidth = 1.2;
  ctx.beginPath();
  for (let i = 0; i <= 48; i++) {
    const a = (i / 48) * Math.PI * 2, r = raio + amp * p.nivel * ruido(a, p.t);
    const x = cx + Math.cos(a) * r, y = cy + Math.sin(a) * r;
    if (i) ctx.lineTo(x, y); else ctx.moveTo(x, y);
  }
  ctx.stroke();
}

function esfera(ctx, cx, cy, raio, p, tam) {
  const rot = p.t * p.giro, c = Math.cos(rot), s = Math.sin(rot), r = raio * (1 + 0.18 * p.nivel);
  for (const [x, y, z] of ESFERA) {
    const xr = x * c + z * s, zr = -x * s + z * c, f = 1 / (1.8 - zr * 0.5);  // perspectiva leve
    const frente = (zr + 1) / 2;
    ctx.fillStyle = rgba(p.cor, p.alfa * (0.15 + 0.6 * frente));
    ctx.beginPath();
    ctx.arc(cx + xr * r * f * 1.5, cy + y * r * f * 1.5, tam * (0.6 + frente), 0, Math.PI * 2);
    ctx.fill();
  }
}

function arcos(ctx, cx, cy, raio, p) {
  ctx.lineWidth = 1.6;
  if (p.spin > 0.05) {  // pensando: um arco girando (spinner)
    ctx.strokeStyle = rgba(p.cor, p.alfa * p.spin);
    const a0 = p.t * 2.4;
    ctx.beginPath();
    ctx.arc(cx, cy, raio, a0, a0 + 1.3);
    ctx.stroke();
  }
  if (p.radar > 0.05) {  // ouvindo: três arcos que se fecham em direção ao núcleo conforme a voz
    ctx.strokeStyle = rgba(p.cor, p.alfa * p.radar * 0.8);
    for (let k = 0; k < 3; k++) {
      const a0 = (k * Math.PI * 2) / 3 + 0.4;
      ctx.beginPath();
      ctx.arc(cx, cy, raio * (1 - 0.1 * p.nivel), a0, a0 + 0.9);
      ctx.stroke();
    }
  }
}

// p = { cor, alfa, giro, spin, radar, nivel (0..1), t (s), modo }
export function desenhar(ctx, largura, altura, p) {
  const cx = largura / 2, cy = altura / 2, min = Math.min(largura, altura), R0 = min * 0.17;
  ctx.clearRect(0, 0, largura, altura);
  ctx.globalCompositeOperation = "lighter";
  if (p.modo === "completo") {
    nucleo(ctx, cx, cy, R0 * (1 + 0.14 * p.nivel), p);
    anel(ctx, cx, cy, R0 * 1.55, rgba(p.cor, p.alfa * 0.3), 1);
    anel(ctx, cx, cy, R0 * 1.95, rgba(p.cor, p.alfa * 0.2), 1);
    esfera(ctx, cx, cy, R0 * 1.3, p, Math.max(0.7, min / 90));
    arcos(ctx, cx, cy, R0 * 1.95, p);
    onda(ctx, cx, cy, R0 * 2.3, min * 0.05, p);
  } else {  // suave ou parado: só brilho e um anel, sem giro nem escala
    nucleo(ctx, cx, cy, R0, { ...p, alfa: p.alfa * (0.75 + 0.25 * p.nivel) });
    anel(ctx, cx, cy, R0 * 1.7, rgba(p.cor, p.alfa * (0.2 + 0.3 * p.nivel)), 1);
  }
  ctx.globalCompositeOperation = "source-over";
}
