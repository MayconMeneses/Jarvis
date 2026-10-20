// As 8 áreas do Second Brain, derivadas do prefixo do nome da nota, e o grafo (nós, ligações, posições) usado pelo painel.
// Funções puras: sem DOM, testáveis em node.
import { fold } from "./util.js";

export const AREAS = [
  { id: "metas", nome: "Metas", cor: "#fbbf24" },
  { id: "trabalho", nome: "Trabalho", cor: "#ff5547" },
  { id: "projetos", nome: "Projetos", cor: "#8b7cff" },
  { id: "financas", nome: "Finanças", cor: "#f7931a" },
  { id: "aprendizado", nome: "Aprendizado", cor: "#2dd4ff" },
  { id: "saude", nome: "Saúde", cor: "#10b981" },
  { id: "relacoes", nome: "Relações", cor: "#ec4899" },
  { id: "meta", nome: "Meta", cor: "#8a90a6" },
];
export const AREA_POR_ID = Object.fromEntries(AREAS.map((a) => [a.id, a]));
export const MAX_NOTAS = 150;

// Primeiro trecho do nome (sem acento, minúsculo) -> área. O que não está aqui cai em "meta".
const PREFIXOS = {
  projetos: "projetos", oficina: "projetos", perfil: "trabalho", trabalho: "trabalho",
  metas: "metas", lembretes: "metas", financas: "financas", saude: "saude", relacoes: "relacoes",
  aprendizado: "aprendizado", lembrancas: "meta", diario: "meta", meta: "meta",
};

export function areaDaNota(ref) {
  const prefixo = fold(String(ref).split("/")[0]).replace(/[^a-z]/g, "");
  return Object.hasOwn(PREFIXOS, prefixo) ? PREFIXOS[prefixo] : "meta";
}

const LIGACAO = /\[\[([^\]\n]{1,120})\]\]/g;

// Nós: núcleo, uma por área e uma por nota (no máximo MAX_NOTAS, repartidas entre as áreas para a Oficina não engolir o resto).
export function construirGrafo(notas, max = MAX_NOTAS) {
  const porArea = new Map(AREAS.map((a) => [a.id, []]));
  for (const n of notas) porArea.get(areaDaNota(n.ref)).push(n);  // `notas` já vem das mais recentes para as mais antigas
  const escolhidas = [];
  for (let i = 0; escolhidas.length < max; i++) {
    let achou = false;
    for (const lista of porArea.values()) if (i < lista.length && escolhidas.length < max) { escolhidas.push(lista[i]); achou = true; }
    if (!achou) break;
  }
  const nos = [{ id: "c", tipo: "nucleo", rotulo: "Jarvis", area: null, grau: 0 }];
  const arestas = [];
  const indice = new Map();
  for (const a of AREAS) {
    nos.push({ id: "a:" + a.id, tipo: "area", rotulo: a.nome, area: a.id, grau: 0 });
    arestas.push({ de: "c", para: "a:" + a.id });
  }
  for (const n of escolhidas) {
    const no = { id: "n:" + n.ref, tipo: "nota", rotulo: n.titulo || n.ref.split("/").pop(), ref: n.ref, area: areaDaNota(n.ref), grau: 0, corpo: n.corpo || "" };
    nos.push(no);
    indice.set(fold(n.ref), no.id);
    indice.set(fold(no.rotulo), no.id);
    arestas.push({ de: "a:" + no.area, para: no.id });
  }
  const unicas = new Set();
  for (const no of nos) {
    if (no.tipo !== "nota") continue;
    for (const m of no.corpo.matchAll(LIGACAO)) {
      const alvo = indice.get(fold(m[1].trim()));
      const chave = alvo && [no.id, alvo].sort().join("\u0000");
      if (alvo && alvo !== no.id && !unicas.has(chave)) { unicas.add(chave); arestas.push({ de: no.id, para: alvo, link: true }); }
    }
    delete no.corpo;
  }
  const porId = new Map(nos.map((n) => [n.id, n]));
  for (const e of arestas) { porId.get(e.de).grau++; porId.get(e.para).grau++; }
  return { nos, arestas, porId, total: notas.length };
}

// Raio do nó pelo número de ligações (links e área). Núcleo e áreas têm tamanho fixo próprio.
export function raioDoNo(no) {
  if (no.tipo === "nucleo") return 13;
  if (no.tipo === "area") return 8;
  return Math.min(9, 3 + Math.sqrt(no.grau) * 1.6);
}

// Posições iniciais (áreas num anel, notas em espiral ao redor da sua área) e algumas rodadas de repulsão e mola.
export function posicionar(grafo, largura, altura, rodadas = 70) {
  const cx = largura / 2, cy = altura / 2, raioAnel = Math.min(largura, altura) * 0.34;
  const pos = new Map([["c", { x: cx, y: cy }]]);
  AREAS.forEach((a, i) => {
    const ang = (i / AREAS.length) * Math.PI * 2 - Math.PI / 2;
    pos.set("a:" + a.id, { x: cx + Math.cos(ang) * raioAnel, y: cy + Math.sin(ang) * raioAnel, ang });
  });
  const contagem = new Map();
  for (const no of grafo.nos) {
    if (no.tipo !== "nota") continue;
    const base = pos.get("a:" + no.area), k = (contagem.get(no.area) || 0) + 1;
    contagem.set(no.area, k);
    const a = k * 2.399963, r = 14 + 7 * Math.sqrt(k);
    pos.set(no.id, { x: base.x + Math.cos(a) * r, y: base.y + Math.sin(a) * r });
  }
  const folga = 10, lista = grafo.nos.filter((n) => n.tipo !== "nucleo");
  for (let it = 0; it < rodadas; it++) {
    for (let i = 0; i < lista.length; i++) for (let j = i + 1; j < lista.length; j++) {  // repulsão suave entre quaisquer dois nós
      const a = pos.get(lista[i].id), b = pos.get(lista[j].id);
      let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy;
      const minimo = raioDoNo(lista[i]) + raioDoNo(lista[j]) + 6;
      if (d2 > minimo * minimo * 9) continue;
      if (d2 < 0.01) { dx = 0.1; dy = 0.1; d2 = 0.02; }
      const d = Math.sqrt(d2), f = Math.max(0, minimo * 1.6 - d) * 0.12;
      a.x += (dx / d) * f; a.y += (dy / d) * f; b.x -= (dx / d) * f; b.y -= (dy / d) * f;
    }
    for (const e of grafo.arestas) {  // molas curtas: nota presa à sua área (a área não se move) e notas ligadas entre si
      if (e.de === "c") continue;
      const a = pos.get(e.de), b = pos.get(e.para), alvo = e.link ? 46 : 26, dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 1, f = (d - alvo) * 0.04;
      if (e.link) { a.x += (dx / d) * f * 0.5; a.y += (dy / d) * f * 0.5; b.x -= (dx / d) * f * 0.5; b.y -= (dy / d) * f * 0.5; } else { b.x -= (dx / d) * f; b.y -= (dy / d) * f; }
    }
    for (const n of lista) {  // mantém as áreas no lugar e tudo dentro da tela
      const p = pos.get(n.id);
      if (n.tipo === "area") { p.x += (cx + Math.cos(p.ang) * raioAnel - p.x) * 0.5; p.y += (cy + Math.sin(p.ang) * raioAnel - p.y) * 0.5; }
      p.x = Math.max(12, Math.min(largura - 12, p.x)); p.y = Math.max(12, Math.min(altura - 12, p.y));
    }
  }
  return pos;
}

// Nó mais próximo do toque (dentro do raio + folga de dedo), ou null.
export function noEm(grafo, pos, x, y, dedo = 14) {
  let melhor = null, dist = Infinity;
  for (const no of grafo.nos) {
    const p = pos.get(no.id), d = Math.hypot(p.x - x, p.y - y);
    if (d <= raioDoNo(no) + dedo && d < dist) { melhor = no; dist = d; }
  }
  return melhor;
}
