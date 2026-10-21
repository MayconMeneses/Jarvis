// Ordem das caixas do HUD (regras PURAS, sem DOM, testáveis no Node). A ordem fica na meta "hud_ordem" do aparelho.
// Por que botões subir/descer e não arrastar livre: no iPhone, segurar e arrastar briga com a rolagem, a seleção de texto e o menu
// de pressionar longo do Safari; os botões são previsíveis, acessíveis (VoiceOver, teclado) e não dependem de gesto.
export const CHAVE = "hud_ordem";
export const PADRAO = ["clima", "vagas", "noticias", "tecnologia", "pc", "pc-vitais", "pc-sessoes", "pc-tarefas", "pc-uso", "pc-radar", "pc-agenda", "pc-emails", "pc-agentes", "uso-ia", "agentes"];

// JSON antigo, corrompido ou hostil -> uma ordem válida: só ids conhecidos, sem repetição, e o que faltar vai ao fim na ordem padrão. Nunca lança.
export function sanear(bruto, ids = PADRAO) {
  const vistos = new Set(), saida = [];
  if (Array.isArray(bruto)) for (const id of bruto.slice(0, 200)) if (typeof id === "string" && ids.includes(id) && !vistos.has(id)) { vistos.add(id); saida.push(id); }
  for (const id of ids) if (!vistos.has(id)) saida.push(id);
  return saida;
}

// Troca `id` com o vizinho visível mais próximo na direção de `delta` (-1 sobe, +1 desce). Sem vizinho, devolve a mesma ordem (limite, sem erro).
export function mover(ordem, id, delta, visiveis = null) {
  const i = ordem.indexOf(id), passo = delta < 0 ? -1 : 1;
  if (i < 0 || !delta) return [...ordem];
  for (let j = i + passo; j >= 0 && j < ordem.length; j += passo) {
    if (visiveis && !visiveis.includes(ordem[j])) continue;
    const nova = [...ordem];
    [nova[i], nova[j]] = [nova[j], nova[i]];
    return nova;
  }
  return [...ordem];
}

// Há vizinho visível naquela direção? (desliga o botão no começo e no fim da lista)
export const podeMover = (ordem, id, delta, visiveis = null) => mover(ordem, id, delta, visiveis).join() !== ordem.join();

export const anuncio = (titulo, ordem, id, visiveis = null) => {
  const lista = visiveis ? ordem.filter((x) => visiveis.includes(x)) : ordem;
  return `${titulo}: posição ${lista.indexOf(id) + 1} de ${lista.length}.`;
};
