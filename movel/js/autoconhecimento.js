// Autoconhecimento: o que a Jarvis sabe sobre ELA MESMA (instalar, copiar a memória, parear, chaves...). Vem de dados/autoconhecimento.json
// (guardado no cache do app, funciona offline). O arquivo é DADO: só texto, tamanho limitado, nunca é executado.
// A resposta se adapta ao aparelho (iPhone/Android/computador) e ao que o app já tem configurado.
import { cortar } from "./util.js";

const MAX_ENTRADAS = 300, MAX_TEXTO = 1200, MAX_LISTA = 40;
const texto = (v, max = MAX_TEXTO) => (typeof v === "string" ? v.trim().slice(0, max) : "");
const lista = (v, max = MAX_TEXTO) => (Array.isArray(v) ? v.slice(0, MAX_LISTA).map((x) => texto(x, max)).filter(Boolean) : []);

// Aceita só o esquema esperado; entrada malformada é descartada em silêncio (o app abre mesmo com o arquivo estragado).
export function sanear(bruto) {
  if (!Array.isArray(bruto)) return [];
  const ids = new Set(), saida = [];
  for (const e of bruto.slice(0, MAX_ENTRADAS)) {
    if (!e || typeof e !== "object") continue;
    const id = texto(e.id, 60);
    if (!/^[\w.-]+$/.test(id) || ids.has(id)) continue;
    ids.add(id);
    const plataformas = lista(e.plataformas, 20).filter((p) => p === "pc" || p === "celular");
    saida.push({ id, titulo: texto(e.titulo, 120) || id, exemplos: lista(e.exemplos, 200), palavras: lista(e.palavras, 60), resposta: texto(e.resposta),
      passos: lista(e.passos), plataformas: plataformas.length ? plataformas : ["pc", "celular"], relacionados: lista(e.relacionados, 60) });
  }
  return saida;
}

export async function carregar(buscar = fetch, url = "dados/autoconhecimento.json") {
  try {
    const r = await buscar(url);
    if (!r.ok) return [];
    return sanear(await r.json());
  } catch { return []; }
}

export const alvos = (entradas) => entradas.map((e) => ({ id: "app:" + e.id, tipo: "app", rotulo: e.titulo, exemplos: [e.titulo, ...e.exemplos], palavras: e.palavras, entrada: e, peso: e.plataformas.includes("celular") ? 1 : 0.93 }));

// ── aparelho ──
export function detectarAparelho({ ua = "", toques = 0, instalado = false } = {}) {
  const ipad = /iPad/.test(ua) || (/Macintosh/.test(ua) && toques > 1);
  if (/iPhone|iPod/.test(ua) || ipad) return { plataforma: "iphone", nome: ipad ? "iPad" : "iPhone", navegador: /CriOS|FxiOS|EdgiOS/.test(ua) ? "outro navegador do iPhone" : "Safari", instalado };
  if (/Android/.test(ua)) return { plataforma: "android", nome: "Android", navegador: "Chrome", instalado };
  return { plataforma: "desktop", nome: "computador", navegador: "navegador", instalado };
}

export function plataformaDaPergunta(frase) {
  const t = String(frase).toLowerCase();
  if (/iphone|ios|safari|ipad|apple/.test(t)) return "iphone";
  if (/android|chrome|samsung|xiaomi|motorola/.test(t)) return "android";
  return null;
}

const MARCA = /(iPhone|iOS|iPad|Android|Chrome)[^:.]{0,30}:\s*/gi;

// Um passo pode servir a um aparelho só ("iPhone: ..."), ou trazer os dois no mesmo texto ("iPhone: ... Android: ...").
export function passoParaAparelho(passo, plataforma) {
  const marcas = [...passo.matchAll(MARCA)];
  if (!plataforma || plataforma === "desktop" || !marcas.length) return passo;
  const qual = (m) => (/android|chrome/i.test(m[1]) ? "android" : "iphone");
  const partes = marcas.map((m, i) => ({ qual: qual(m), texto: passo.slice(m.index + m[0].length, i + 1 < marcas.length ? marcas[i + 1].index : passo.length).trim() }));
  const antes = passo.slice(0, marcas[0].index).trim();
  const meu = partes.find((p) => p.qual === plataforma);
  if (!meu) return antes ? passo : "";  // o passo é só de outro aparelho
  return [antes, meu.texto].filter(Boolean).join(" ");
}

export const passosDoAparelho = (passos, plataforma) => passos.map((p) => passoParaAparelho(p, plataforma)).filter(Boolean);

const MIGRACAO = /outro|novo|trocar|migr|transfer|passar|mudei|levar/i;
const ehMigracao = (e) => MIGRACAO.test(e.id + " " + e.titulo);

// Para qual aparelho mostrar os passos: o que a pessoa citou na pergunta; senão (e se não for troca de celular) o aparelho atual.
export function plataformaDosPassos(entrada, frase, aparelho) {
  return plataformaDaPergunta(frase) || (ehMigracao(entrada) ? null : (aparelho?.plataforma !== "desktop" ? aparelho?.plataforma : null)) || null;
}

// ── estado do app ──
const TEMA = {
  copia: /copia|backup|restaur|outro-cel|trocar|migr|novo-ap|aparelho/i, chaves: /gemini|chave|nuvem|api|nvidia|brave/i, pc: /parear|pareamento|pc-|^pc|computador/i,
  foco: /foco|escuta|microfone|voz/i, atualizar: /atualiz|versao/i, instalar: /instal|tela-inicial|pwa/i,
};
const dataCurta = (iso) => { const d = new Date(iso); return Number.isNaN(+d) ? "" : `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}/${d.getFullYear()}`; };

// Linhas e botões extras que dependem do que o app já tem. `estado` vem do main: { ultimaCopia, nuvem, pc, cerebro }.
export function complementos(entrada, estado = {}, frase = "") {
  const chave = (entrada.id + " " + entrada.titulo + " " + entrada.palavras.join(" ")), linhas = [], botoes = [];
  if (TEMA.copia.test(chave)) {
    if (estado.ultimaCopia) linhas.push(`Sua última cópia de segurança foi feita em ${dataCurta(estado.ultimaCopia)}. Se mudou muita coisa desde então, faça outra antes de trocar de aparelho.`);
    else { linhas.push("**Você ainda não fez a cópia de segurança neste aparelho.** Sem ela, nada da sua memória vai para o outro celular."); botoes.push({ rotulo: "Fazer a cópia agora", abrir: { aba: "memoria", foco: "senha-copia" } }); }
    if (ehMigracao(entrada)) {
      const sem = [estado.nuvem && "as chaves de IA que você cadastrou", estado.pc && "o pareamento com o PC"].filter(Boolean);
      if (sem.length) linhas.push(`Neste aparelho você tem ${sem.join(" e ")}: isso **não** vai na cópia, então cadastre de novo no outro.`);
    }
  }
  if (TEMA.chaves.test(chave) && !ehMigracao(entrada)) {
    if (estado.nuvem === false) { linhas.push("Você ainda não cadastrou nenhuma chave de IA neste aparelho."); botoes.push({ rotulo: "Abrir o painel de chaves", abrir: { aba: "cerebro", foco: "nv-provedor" } }); }
    else if (estado.nuvem) linhas.push("Já há uma chave cadastrada neste aparelho.");
  }
  if (TEMA.pc.test(chave) && !ehMigracao(entrada) && estado.pc !== undefined) {
    linhas.push(estado.pc ? "Este aparelho já está pareado com o PC." : "Este aparelho ainda não está pareado com o PC.");
    botoes.push({ rotulo: "Abrir o Início", abrir: { aba: "hud" } });
  }
  if (TEMA.foco.test(chave) && !/gemini|chave/.test(chave)) botoes.push({ rotulo: "Abrir o modo foco", foco: true });
  if (TEMA.instalar.test(chave) && estado.instalado) linhas.push("Aliás, este app já está instalado na tela inicial deste aparelho.");
  return { linhas, botoes: botoes.slice(0, 3) };
}

// Texto final em Markdown. `relacionadas` são entradas vizinhas (por id) para o "Veja também".
export function formatar(entrada, { aparelho, frase = "", estado = {}, relacionadas = [] } = {}) {
  const plat = plataformaDosPassos(entrada, frase, aparelho);
  const partes = [];
  const soPc = !entrada.plataformas.includes("celular");
  if (soPc) partes.push("_Isto é do Jarvis do PC; no celular você só vê o resultado._");
  partes.push(`**${entrada.titulo}**`);
  if (entrada.resposta) partes.push(entrada.resposta);
  const passos = passosDoAparelho(entrada.passos, plat);
  if (passos.length) {
    if (plat) partes.push(`_Passos para ${plat === "iphone" ? "iPhone (Safari)" : "Android (Chrome)"}:_`);
    partes.push(passos.map((p, i) => `${i + 1}. ${p}`).join("\n"));
  }
  const extra = complementos(entrada, estado, frase);
  if (extra.linhas.length) partes.push(extra.linhas.join("\n"));
  const vizinhas = relacionadas.slice(0, 3);
  if (vizinhas.length) partes.push("Veja também: " + vizinhas.map((v) => `"${cortar(v.titulo, 50)}"`).join(", ") + ".");
  return { texto: partes.join("\n\n"), botoes: extra.botoes };
}
