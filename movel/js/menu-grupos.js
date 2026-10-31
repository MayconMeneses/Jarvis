// Menu ☰ agrupado (Ver, Saber e fazer, Ajustes, Conversa): a lista e as regras PURAS (sem DOM, testáveis no Node).
// Cada item aponta para uma aba (aba) que já existe na página e pode, depois de abrir a aba, clicar num botão (clicar), abrir um painel
// <details> (abrir) ou rolar até um bloco (rolarPara). acao cobre o que não é aba ("foco"). Abas que ninguém listou vão para "Saber e fazer".
export const GRUPOS = [
  { id: "ver", rotulo: "Ver", itens: [
    { id: "inicio", rotulo: "Início", aba: "hud" },
    { id: "conversa", rotulo: "Conversa", aba: "conversa" },
    { id: "pc", rotulo: "Seu PC (somente leitura)", aba: "hud", rolarPara: "item-pc" },
    { id: "noticias", rotulo: "Notícias e Radar", aba: "noticias" },
    { id: "memoria", rotulo: "Memória", aba: "memoria" },
    { id: "grafo", rotulo: "Grafo da memória", aba: "memoria", clicar: "ver-grafo" },
  ] },
  { id: "saber", rotulo: "Saber e fazer", itens: [
    { id: "oficina", rotulo: "Oficina", aba: "oficina" },
    { id: "documentos", rotulo: "Documentos", aba: "documentos" },
    { id: "instagram", rotulo: "Instagram", aba: "instagram" },
    { id: "cerebro", rotulo: "Cérebro e nuvem", aba: "cerebro" },
  ] },
  { id: "ajustes", rotulo: "Ajustes", itens: [
    { id: "aparencia", rotulo: "Aparência e efeitos", aba: "cerebro", abrir: "painel-aparencia" },
    { id: "perfil", rotulo: "Meu perfil", aba: "cerebro", abrir: "painel-perfil" },
    { id: "uso", rotulo: "Uso de IA", aba: "cerebro", abrir: "painel-uso" },
    { id: "agentes", rotulo: "Agentes", aba: "cerebro", abrir: "painel-agentes" },
    { id: "pareado", rotulo: "PC pareado", aba: "cerebro", abrir: "pc-bloco" },
  ] },
  { id: "conversa", rotulo: "Conversa", itens: [
    { id: "nova", rotulo: "Nova conversa", aba: "conversa", clicar: "nova-conversa" },
    { id: "voz", rotulo: "Conversar por voz", aba: "conversa", clicar: "voz-modo" },
    { id: "foco", rotulo: "Modo foco (orbe em tela cheia)", acao: "foco" },
  ] },
];

// abas: [{ id, rotulo }] das abas que existem agora. Devolve os grupos só com o que dá para abrir.
export function montarMenu(abas, grupos = GRUPOS) {
  const ids = new Set(abas.map((a) => a.id)), listadas = new Set(grupos.flatMap((g) => g.itens.map((i) => i.aba).filter(Boolean)));
  const saida = grupos.map((g) => ({ ...g, itens: g.itens.filter((i) => i.acao || ids.has(i.aba)) }));
  const outras = abas.filter((a) => !listadas.has(a.id));
  const alvo = saida.find((g) => g.id === "saber");
  if (outras.length && alvo) alvo.itens = [...alvo.itens, ...outras.map((a) => ({ id: `aba-${a.id}`, rotulo: a.rotulo || a.id, aba: a.id }))];
  return saida.filter((g) => g.itens.length);
}

// Setas circulares, Home/End. Outra tecla: null.
export function proximoItem(atual, total, tecla) {
  if (!(total > 0)) return null;
  if (tecla === "ArrowDown") return atual < 0 ? 0 : (atual + 1) % total;
  if (tecla === "ArrowUp") return atual < 0 ? total - 1 : (atual - 1 + total) % total;
  if (tecla === "Home") return 0;
  if (tecla === "End") return total - 1;
  return null;
}

// Em qual item do menu a aba atual "mora" (para marcar aria-current): o primeiro item que só abre a aba, sem painel nem clique extra.
export const itemAtual = (grupos, aba) => grupos.flatMap((g) => g.itens).find((i) => i.aba === aba && !i.clicar && !i.abrir && !i.rolarPara)?.id || null;
