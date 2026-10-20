// Aba Memória > Grafo: o Second Brain em Canvas. Nó = nota (até 150), tamanho = ligações ([[nota]] e área), cor = área.
// Toque num nó abre a nota no editor. Pouco movimento parado (12 fps), pausa com a aba oculta ou o painel fechado, e fica parado
// com "reduzir movimento" (escolha do orbe: suave/desligado).
import { AREAS, construirGrafo, noEm, posicionar } from "./areas.js";
import { desenharGrafo } from "./grafo-desenho.js";
import { modoEfetivo } from "./orbe.js";

const $ = (id) => document.getElementById(id);
const FPS_PARADO = 12, FPS_ATIVO = 30, ALTURA = 360;

export function ligarGrafo({ memoria, aoAbrirNota }) {
  const canvas = $("grafo"), ctx = canvas.getContext("2d");
  let grafo = null, pos = null, lugar = null, largura = 300, id = null, ultimo = 0, ativoAte = 0, selecionado = null, t = 0, animar = true;
  let pulsos = [];

  const legenda = () => {
    const contagem = new Map(AREAS.map((a) => [a.id, 0]));
    for (const n of grafo.nos) if (n.tipo === "nota") contagem.set(n.area, contagem.get(n.area) + 1);
    $("grafo-legenda").replaceChildren(...AREAS.map((a) => {
      const li = document.createElement("li"), cor = document.createElement("span");
      cor.className = "cor"; cor.style.background = a.cor;
      li.append(cor, `${a.nome} ${contagem.get(a.id)}`);
      return li;
    }));
  };

  const desenhar = () => { lugar = desenharGrafo(ctx, grafo, pos, largura, ALTURA, { t, pulsos: animar ? pulsos : [], selecionado, animar }); };
  const parado = () => document.hidden || !canvas.offsetParent;  // aba oculta, painel fechado ou outra aba do app

  function quadro(ts) {
    id = null;
    if (parado() || !grafo) return;
    if (animar) id = requestAnimationFrame(quadro);
    const fps = ts < ativoAte ? FPS_ATIVO : FPS_PARADO;
    if (ts - ultimo < 1000 / fps - 2) return;
    const dt = Math.min(0.1, (ts - ultimo) / 1000 || 0.05);
    ultimo = ts; t += dt;
    pulsos = pulsos.map((p) => ({ ...p, u: p.u + dt * 0.5 })).filter((p) => p.u < 1);
    if (pulsos.length < 4 && grafo.arestas.length && Math.random() < 0.12) pulsos.push({ aresta: Math.floor(Math.random() * grafo.arestas.length), u: 0 });
    desenhar();
  }
  const acordar = () => { if (id === null && grafo && !parado()) id = requestAnimationFrame(quadro); };

  async function mostrar() {
    const reduzir = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)").matches : false;
    animar = modoEfetivo(await memoria.meta("orbe_modo"), reduzir) === "completo";
    grafo = construirGrafo(await memoria.listar());
    largura = Math.max(200, canvas.parentElement.clientWidth || 300);
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    canvas.width = Math.round(largura * dpr); canvas.height = Math.round(ALTURA * dpr);
    canvas.style.height = ALTURA + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    pos = posicionar(grafo, largura, ALTURA);
    selecionado = null; pulsos = [];
    canvas.setAttribute("aria-label", `Grafo da memória: ${grafo.nos.filter((n) => n.tipo === "nota").length} notas em 8 áreas. A lista de notas mostra o mesmo conteúdo em texto.`);
    $("grafo-info").textContent = grafo.total > 150 ? `Mostrando 150 de ${grafo.total} notas (repartidas entre as áreas).` : "Toque num ponto para abrir a nota.";
    legenda();
    desenhar();
    acordar();
  }

  canvas.addEventListener("click", async (ev) => {
    if (!grafo) return;
    const r = canvas.getBoundingClientRect(), no = noEm(grafo, pos, ev.clientX - r.left, ev.clientY - r.top);
    ativoAte = performance.now() + 1500;
    selecionado = no ? no.id : null;
    if (no) $("grafo-info").textContent = no.tipo === "nota" ? `${no.ref}` : `${no.rotulo}: ${no.grau - (no.tipo === "area" ? 1 : 0)} ${no.tipo === "area" ? "notas" : "áreas"}`;
    desenhar(); acordar();
    if (no?.tipo === "nota") { const nota = await memoria.ler(no.ref); if (nota) aoAbrirNota(nota); }
  });
  document.addEventListener("visibilitychange", acordar);
  return { mostrar, ocultar: () => { if (id !== null) { cancelAnimationFrame(id); id = null; } } };
}
