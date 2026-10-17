// Ferramentas de design (mesmos cálculos do PC): contraste WCAG, paleta, escala tipográfica, espaçamento e tokens CSS.
export function paraRgb(cor) {
  let hexa = String(cor).trim().replace(/^#/, "");
  if (/^[0-9a-f]{3}$/i.test(hexa)) hexa = [...hexa].map((c) => c + c).join("");
  if (!/^[0-9a-f]{6}$/i.test(hexa)) throw new Error(`cor inválida: ${cor} (use #rgb ou #rrggbb)`);
  return [0, 2, 4].map((i) => parseInt(hexa.slice(i, i + 2), 16));
}

export function luminancia(cor) {
  const [r, g, b] = paraRgb(cor).map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function contraste(a, b) {
  const [claro, escuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (escuro + 0.05);
}

export function avaliarContraste(texto, fundo) {
  const razao = contraste(texto, fundo);
  const ok = (min) => (razao >= min ? "passa" : "FALHA");
  return `**Contraste ${texto} sobre ${fundo}: ${razao.toFixed(2)}:1**\n- Texto normal (AA, mínimo 4,5:1): ${ok(4.5)}\n- Texto grande (AA, mínimo 3:1): ${ok(3)}\n`
    + `- Texto normal (AAA, mínimo 7:1): ${ok(7)}\n- Componentes de interface e ícones (mínimo 3:1): ${ok(3)}`;
}

function rgbParaHls([r, g, b]) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
  if (max === min) return [0, l, 0];
  const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, l, s];
}

function hlsParaHex(h, l, s) {
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
  const canal = (t) => {
    t = (t + 1) % 1;
    const v = t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
    return Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, "0");
  };
  return s === 0 ? "#" + canal(0).repeat(0) + [l, l, l].map((v) => Math.round(v * 255).toString(16).padStart(2, "0")).join("") : "#" + [h + 1 / 3, h, h - 1 / 3].map(canal).join("");
}

const TONS = { 50: 0.96, 100: 0.92, 200: 0.84, 300: 0.74, 400: 0.62, 500: 0.5, 600: 0.42, 700: 0.34, 800: 0.26, 900: 0.18 };

export function paleta(cor) {
  const [h, , s] = rgbParaHls(paraRgb(cor));
  return Object.fromEntries(Object.entries(TONS).map(([nome, luz]) => [nome, hlsParaHex(h, luz, s)]));
}

const NOMES_TAMANHO = ["xs", "sm", "base", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl"];

export function escalaTipografica(base = 16, razao = 1.25, passos = 6) {
  const saida = [];
  for (let i = -2; i < passos - 1; i++) saida.push([NOMES_TAMANHO[i + 2], Math.round(base * razao ** i * 100) / 100]);
  return saida.slice(0, NOMES_TAMANHO.length);
}

export const escalaEspacamento = (base = 4, passos = 10) => [1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24].slice(0, passos).map((n) => base * n);

export function tokensCss(cor, base = 16, razao = 1.25) {
  const linhas = [":root {"];
  for (const [n, v] of Object.entries(paleta(cor))) linhas.push(`  --cor-${n}: ${v};`);
  for (const [n, t] of escalaTipografica(base, razao)) linhas.push(`  --texto-${n}: ${+(t / 16).toFixed(4)}rem;`);
  escalaEspacamento().forEach((v, i) => linhas.push(`  --espaco-${i + 1}: ${+(v / 16).toFixed(4)}rem;`));
  linhas.push("  --raio: 0.5rem;", "  --duracao: 200ms;", "}", "@media (prefers-color-scheme: dark) { :root { color-scheme: dark; } }",
    "@media (prefers-reduced-motion: reduce) { * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; } }");
  return linhas.join("\n");
}

export function relatorioPaleta(cor) {
  const linhas = [`**Paleta a partir de ${cor}** (contraste do tom sobre branco / sobre preto):`];
  for (const [n, v] of Object.entries(paleta(cor))) linhas.push(`- ${n}: \`${v}\` — ${contraste(v, "#ffffff").toFixed(1)}:1 / ${contraste(v, "#000000").toFixed(1)}:1`);
  linhas.push("Dica: texto normal precisa de pelo menos 4,5:1; use tons 700–900 para texto sobre fundo claro.");
  return linhas.join("\n");
}

export function relatorioEscala(base = 16, razao = 1.25) {
  return `**Escala tipográfica (base ${base}px, razão ${razao}):** ${escalaTipografica(base, razao).map(([n, t]) => `${n} ${t}px`).join(", ")}\n`
    + `**Espaçamento (grade de 4px):** ${escalaEspacamento().map((v) => v + "px").join(", ")}`;
}
