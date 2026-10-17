// Aprender e pesquisar na internet pelo próprio celular: Wikipédia em português (aceita chamadas do navegador).
// O que vem da web é dado de terceiros e NÃO verificado: vira nota "Aprendizado/<tema>" que o usuário vê e apaga.
const API = "https://pt.wikipedia.org";

export async function buscarWikipedia(tema, buscar = fetch.bind(globalThis)) {
  const url = `${API}/w/api.php?action=query&list=search&srsearch=${encodeURIComponent(tema)}&srlimit=3&format=json&origin=*`;
  const resposta = await buscar(url);
  if (!resposta.ok) throw new Error(`a Wikipédia respondeu ${resposta.status}`);
  const achados = (await resposta.json())?.query?.search || [];
  if (!achados.length) return null;
  const titulo = achados[0].title;
  const resumo = await buscar(`${API}/api/rest_v1/page/summary/${encodeURIComponent(titulo)}`);
  const dados = resumo.ok ? await resumo.json() : {};
  return {
    titulo,
    resumo: String(dados.extract || achados[0].snippet.replace(/<[^>]+>/g, "")).slice(0, 1500),
    fonte: dados.content_urls?.desktop?.page || `${API}/wiki/${encodeURIComponent(titulo.replace(/ /g, "_"))}`,
    outros: achados.slice(1).map((a) => a.title),
  };
}

export const temaDe = (texto) => texto.replace(/^\s*(aprend\w+|estud\w+|pesquis\w+)\b\s*(sobre\b|a respeito de\b|por\b)?\s*/i, "").replace(/[?!. ]+$/g, "").slice(0, 80);

export async function aprender(texto, memoria, buscar) {
  const tema = temaDe(texto);
  if (tema.length < 3) return 'Sobre o que quer que eu aprenda? Exemplo: "aprenda sobre computação quântica".';
  let achado;
  try { achado = await buscarWikipedia(tema, buscar); } catch (e) { return `Não consegui aprender sobre "${tema}": ${e.message} (sem internet?).`; }
  if (!achado) return `Não encontrei nada sobre "${tema}" na Wikipédia.`;
  const corpo = `${achado.resumo}\n\nFonte: ${achado.fonte}\n\n_Aprendido da internet; não verificado. Revise antes de confiar._`;
  await memoria.guardar(`Aprendizado/${tema}`, corpo, "aprendizado", achado.titulo);
  return `Aprendi sobre **${achado.titulo}** e guardei na memória como "Aprendizado/${tema}" (você vê, edita e apaga na aba Memória). Vem da Wikipédia e não foi verificado.\n\n${corpo}`;
}

export async function pesquisar(texto, buscar) {
  const tema = temaDe(texto);
  try {
    const achado = await buscarWikipedia(tema, buscar);
    if (!achado) return `Não encontrei resultados para "${tema}".`;
    return `**${achado.titulo}** (Wikipédia)\n${achado.resumo}\n\nFonte: ${achado.fonte}` + (achado.outros.length ? `\nVeja também: ${achado.outros.join(", ")}.` : "");
  } catch (e) { return `Não consegui pesquisar: ${e.message} (sem internet?).`; }
}

export async function consultarAprendido(tema, memoria) {
  const achado = (await memoria.buscar(tema, 5)).find((n) => n.ref.startsWith("Aprendizado/"));
  return achado ? achado.corpo.slice(0, 2500) : null;
}
