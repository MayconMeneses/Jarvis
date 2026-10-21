// Caixas (Clima, Vagas, Notícias, Tecnologia) com estados carregando/vazio/erro/ok e cópia; cliente do Worker (/saude, /rss, /ler) com reserva;
// fontes de notícias (direto, Worker, rss2json); comandos de chat ("notícias de X", "ler notícia N", "parar").
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { montar as clima } from "../js/caixa-clima.js";
import { montar as noticias } from "../js/caixa-noticias.js";
import { montar as tecnologia } from "../js/caixa-tecnologia.js";
import { montar as vagas } from "../js/caixa-vagas.js";
import { linkSeguro } from "../js/caixa-base.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { carregarFeed, manchetes, porAssunto, separarFonte } from "../js/noticias-fontes.js";
import { criarContexto } from "../js/noticias-ctx.js";
import { ErroRede, Proxy, baseDoProxy, urlSegura } from "../js/rede-proxy.js";
import { Saber } from "../js/saber.js";
import { achar, instalarDom } from "./dom-falso.mjs";

instalarDom();
const ler = (n) => readFileSync(new URL(`./fixtures/${n}`, import.meta.url), "utf8");
const saber = new Saber(JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8")));
const resposta = (corpo, status = 200) => ({ ok: status < 400, status, text: async () => (typeof corpo === "string" ? corpo : JSON.stringify(corpo)), json: async () => (typeof corpo === "string" ? JSON.parse(corpo) : corpo) });
const BASE = "https://proxy.exemplo.workers.dev";
const HOSTS = { "agencia-brasil": "agenciabrasil.ebc.com.br", g1: "g1.globo.com", tecnoblog: "tecnoblog.net", "bbc-brasil": "feeds.bbci.co.uk" };
const feedDe = (url) => { const f = Object.entries(HOSTS).find(([, h]) => url.includes(h)); return f ? ler(`${f[0]}.xml`) : null; };

function rede({ worker = true, saude = { rotas: ["rss", "ler", "ical"], versao: 2 } } = {}) {
  const chamadas = [];
  const buscar = async (url, op = {}) => {
    chamadas.push({ url, op });
    const u = new URL(url);
    if (u.origin === BASE) {
      if (!worker) throw new TypeError("Failed to fetch");
      if (u.pathname === "/saude") return saude ? resposta(saude) : resposta({}, 404);
      const alvo = decodeURIComponent(u.searchParams.get("url") || "");
      if (u.pathname === "/rss") { const x = feedDe(alvo); return x ? resposta(x) : resposta({ erro: "x" }, 502); }
      if (u.pathname === "/ler") return resposta({ titulo: "T", texto: "Texto do artigo.", idioma: "pt-BR", url_final: alvo, tamanho: 16 });
    }
    if (url.includes("agenciabrasil")) return resposta(ler("agencia-brasil.xml"));
    if (url.includes("hacker-news") && url.endsWith("topstories.json")) return resposta([1, 2]);
    if (url.includes("hacker-news")) return resposta({ id: 1, title: "Show HN: um projeto", url: "https://hn.exemplo/1", time: 1792580000 });
    if (url.includes("geocoding")) return resposta({ results: [{ name: "Fortaleza", admin1: "Ceará", latitude: -3.7, longitude: -38.5 }] });
    if (url.includes("api.open-meteo")) return resposta({ current: { temperature_2m: 29.6, apparent_temperature: 33.2, weather_code: 2, relative_humidity_2m: 70, wind_speed_10m: 12 }, daily: { temperature_2m_max: [31], temperature_2m_min: [25], precipitation_probability_max: [40] } });
    if (url.includes("api.github.com")) return resposta([{ title: "Dev Python <img src=x onerror=alert(1)>", labels: [{ name: "Python" }], body: "", html_url: "https://github.com/x/vagas/issues/1", created_at: "2026-10-19T10:00:00Z" }]);
    if (url.includes("remotive")) return resposta({ jobs: [] });
    return resposta("", 404);
  };
  return { buscar, chamadas, proxy: new Proxy({ base: async () => (worker !== null ? BASE : null), buscar }) };
}

test("urlSegura: só https, sem usuário e senha; o Worker é chamado sem cookies nem cabeçalhos próprios", async () => {
  assert.equal(urlSegura(" https://g1.globo.com/rss/g1/ "), "https://g1.globo.com/rss/g1/");
  for (const ruim of ["http://x.org", "ftp://x.org", "https://u:p@x.org", "javascript:alert(1)", "", "x".repeat(3000), "https://x.org/" + "a".repeat(2100)]) assert.throws(() => urlSegura(ruim), ErroRede, ruim.slice(0, 30));
  const r = rede();
  await r.proxy.rss("https://g1.globo.com/rss/g1/");
  const pedido = r.chamadas.at(-1);
  assert.equal(pedido.op.credentials, "omit");
  assert.ok(!pedido.op.headers && !pedido.op.method, "requisição simples: sem preflight");
  await assert.rejects(r.proxy.rss("http://g1.globo.com/"), /https/);
});

test("Worker: /saude mostra as rotas (guardado 10 min); sem Worker, antigo, quebrado ou sem a rota o app segue com a reserva", async () => {
  let t = 0;
  const r = rede(), proxy = new Proxy({ base: async () => BASE, buscar: r.buscar, agora: () => t });
  assert.equal(await proxy.temRota("rss"), true);
  assert.equal(await proxy.temRota("ler"), true);
  assert.equal(await proxy.temRota("outra"), false);
  assert.equal(r.chamadas.filter((c) => c.url.endsWith("/saude")).length, 1, "uma só consulta");
  t += 11 * 60000;
  await proxy.temRota("rss");
  assert.equal(r.chamadas.filter((c) => c.url.endsWith("/saude")).length, 2);
  assert.equal(await new Proxy({ base: async () => null }).rotas(), null);
  for (const cenario of [rede({ saude: null }), rede({ worker: false }), rede({ saude: { rotas: ["nvidia"] } }), rede({ saude: { rotas: "x" } })]) assert.equal(await cenario.proxy.temRota("rss"), false);
  assert.deepEqual([...await rede({ saude: { rotas: ["/rss", "ler"] } }).proxy.rotas()], ["rss", "ler"]);
});

test("Worker: /ler confere o contrato (texto, idioma, url_final) e rejeita respostas fora dele", async () => {
  const r = rede();
  const lido = await r.proxy.ler("https://x.org/a");
  assert.deepEqual([lido.titulo, lido.texto, lido.idioma, lido.urlFinal], ["T", "Texto do artigo.", "pt", "https://x.org/a"]);
  const outro = (corpo, status = 200) => new Proxy({ base: async () => BASE, buscar: async () => resposta(corpo, status) });
  await assert.rejects(outro({ erro: "x" }, 415).ler("https://x.org/a"), /HTTP 415/);
  await assert.rejects(outro({ erro: "limite" }, 429).ler("https://x.org/a"), /HTTP 429/);
  await assert.rejects(outro({ texto: "" }).ler("https://x.org/a"), /texto legível/);
  await assert.rejects(outro("não é json").ler("https://x.org/a"), ErroRede);
  const sujo = await outro({ titulo: 5, texto: "ok" + "z".repeat(50000), idioma: "<script>", url_final: "javascript:1", tamanho: "x" }).ler("https://x.org/a");
  assert.ok(sujo.texto.length <= 20000 && sujo.idioma === "" && sujo.urlFinal === "" && sujo.titulo === "");
  await assert.rejects(new Proxy({ base: async () => BASE, buscar: async () => resposta("x".repeat(3_100_000)) }).rss("https://x.org/f"), /grande demais/);
  const lento = new Proxy({ base: async () => BASE, timeoutMs: 20, buscar: () => new Promise(() => {}) });
  await assert.rejects(lento.rss("https://x.org/f"), /demorou demais/);
});

test("base do Worker vem do proxy já cadastrado (Brave sem /v1, NVIDIA com /v1); lixo é ignorado", async () => {
  const nuvem = (brave, nvidia) => ({ brave: async () => brave, armazem: { ler: async () => nvidia } });
  assert.equal(await baseDoProxy(nuvem({ base: `${BASE}/` })), BASE);
  assert.equal(await baseDoProxy(nuvem(null, { base: `${BASE}/v1` })), BASE);
  for (const ruim of [null, { base: "http://x.org" }, { base: "https://x.org/caminho" }, { base: "javascript:1" }]) assert.equal(await baseDoProxy(nuvem(ruim, null)), null);
  assert.equal(await baseDoProxy(null), null);
});

test("fontes: Agência Brasil direto (CORS), G1 pelo Worker, e sem Worker cai na reserva rss2json", async () => {
  const com = rede();
  const direto = await carregarFeed({ nome: "Agência Brasil", url: "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml", nota: 7 }, com);
  assert.equal(direto.via, "direto");
  assert.ok(!com.chamadas.some((c) => c.url.startsWith(BASE)));
  const g1 = await carregarFeed({ nome: "G1", url: "https://g1.globo.com/rss/g1/", nota: 7, idioma: "pt" }, com);
  assert.equal(g1.via, "worker");
  assert.equal(g1.artigos.length, 4);
  assert.equal(g1.artigos[0].idioma, "pt");
  const sem = rede({ worker: false });
  await assert.rejects(carregarFeed({ nome: "G1", url: "https://g1.globo.com/rss/g1/" }, sem), /sem Worker|reserva/);
  const reserva = async (url) => (url.includes("rss2json") ? resposta({ items: [{ title: "Manchete reserva", link: "https://g1.globo.com/x", pubDate: "2026-10-21 09:00:00" }] }) : resposta("", 500));
  const viaReserva = await carregarFeed({ nome: "G1", url: "https://g1.globo.com/rss/g1/" }, { buscar: reserva, proxy: new Proxy({ base: async () => null, buscar: reserva }) });
  assert.equal(viaReserva.via, "reserva");
  assert.equal(viaReserva.artigos[0].titulo, "Manchete reserva");
  const quebrado = rede({ saude: { rotas: ["rss"] } });  // Worker responde /saude mas o feed dá 502 e a reserva 404: erro com motivo
  await assert.rejects(carregarFeed({ nome: "X", url: "https://exemplo.org/feed" }, quebrado), /Worker: HTTP 502/);
});

test("manchetes alternam os veículos, tiram repetidas e uma fonte fora do ar vira aviso", async () => {
  const r = rede();
  const { itens, avisos } = await manchetes("gerais", { buscar: r.buscar, proxy: r.proxy, limite: 6 });
  assert.equal(itens.length, 6);
  assert.deepEqual(itens.slice(0, 3).map((i) => i.fonte).sort(), ["Agência Brasil", "BBC Brasil", "G1"]);
  assert.deepEqual(avisos, []);
  const tec = await manchetes("tecnologia", { buscar: r.buscar, proxy: r.proxy, limite: 8 });
  assert.ok(tec.itens.some((i) => i.fonte === "Hacker News" && i.idioma === "en"));
  assert.ok(tec.avisos.some((a) => a.startsWith("Canaltech")), "Canaltech sem fixture: aviso, resto segue");
  const nada = await manchetes("gerais", { buscar: async () => { throw new TypeError("offline"); }, proxy: null });
  assert.deepEqual(nada.itens, []);
  assert.equal(nada.avisos.length, 3);
});

test("notícias por assunto: só pelo Worker, separa a fonte do título e guarda 45 minutos", async () => {
  assert.deepEqual(separarFonte("Selic sobe - Valor Econômico"), ["Selic sobe", "Valor Econômico"]);
  assert.deepEqual(separarFonte("Sem fonte nenhuma"), ["Sem fonte nenhuma", "Google News"]);
  const gn = `<rss><channel><item><title>Dólar fecha em alta - Folha</title><link>https://news.google.com/a</link><pubDate>Wed, 21 Oct 2026 10:00:00 GMT</pubDate></item><item><title>Dólar fecha em alta - UOL</title><link>https://news.google.com/b</link><pubDate>Wed, 21 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>`;
  let pedidos = 0;
  const buscar = async (url) => { const u = new URL(url); if (u.pathname === "/saude") return resposta({ rotas: ["rss"] }); pedidos++; return resposta(gn); };
  const proxy = new Proxy({ base: async () => BASE, buscar });
  let t = 1_000_000;
  const a = await porAssunto("dólar hoje", { proxy, agora: () => t });
  assert.equal(a.itens.length, 1);
  assert.deepEqual([a.itens[0].titulo, a.itens[0].fonte], ["Dólar fecha em alta", "Folha"]);
  await porAssunto("dólar hoje", { proxy, agora: () => t + 60000 });
  assert.equal(pedidos, 1);
  await porAssunto("dólar hoje", { proxy, agora: () => t + 46 * 60000 });
  assert.equal(pedidos, 2);
  assert.deepEqual((await porAssunto("x", { proxy: null })).avisos, ["sem Worker"]);
});

const ctxDe = (r, memoria = new Memoria()) => ({ memoria, buscar: r.buscar, proxy: r.proxy, noticias: { ultima: [] }, agendar: () => () => {}, ouvir() {} });

test("caixa de notícias: carregando -> ok, textContent, links só http(s), botões de ouvir e lista numerada para o chat", async () => {
  const raiz = document.createElement("div"), ctx = ctxDe(rede());
  const caixa = noticias(raiz, ctx);
  assert.equal(caixa.estado(), "carregando");
  await caixa.pronto;
  assert.equal(caixa.estado(), "ok");
  const links = achar(raiz, (n) => n.tag === "a");
  assert.ok(links.length >= 6 && links.every((a) => /^https?:\/\//.test(a.href) && a.rel === "noopener noreferrer" && a.target === "_blank"));
  assert.ok(achar(raiz, (n) => n.tag === "button" && n.textContent === "Ouvir").length >= 6);
  assert.ok(ctx.noticias.ultima.length >= 6);
  assert.equal(linkSeguro("x", "javascript:alert(1)").tag, "span");
  assert.equal(linkSeguro("x", "https://x.org").tag, "a");
  assert.match(raiz.textContent, /Atualizado às \d\d:\d\d/);
  caixa.parar();
});

test("caixa com título malicioso: o HTML vira texto inerte", async () => {
  const xml = `<rss><channel><item><title><![CDATA[<img src=x onerror=alert(1)><script>roubar()</script>Manchete]]></title><link>https://x.org/1</link><pubDate>${new Date().toUTCString()}</pubDate></item></channel></rss>`;
  const buscar = async (url) => (url.includes("agenciabrasil") ? resposta(xml) : resposta("", 500));
  const raiz = document.createElement("div");
  const caixa = noticias(raiz, { ...ctxDe(rede()), buscar, proxy: null });
  await caixa.pronto;
  const texto = raiz.textContent;
  assert.ok(texto.includes("Manchete") && !/<|onerror|roubar/.test(texto));
  assert.ok(achar(raiz, (n) => n.tag === "script" || n.tag === "img").length === 0);
  caixa.parar();
});

test("caixa: erro com cópia mostra a cópia datada; erro sem cópia pede para tentar de novo; vazio tem mensagem; atualizar só depois do prazo", async () => {
  const memoria = new Memoria(), r = rede();
  let cair = false, relogio = 1_800_000_000_000, quantas = 0;
  const buscar = async (u, o) => { if (cair) throw new TypeError("offline"); quantas++; return r.buscar(u, o); };
  const ctx = { ...ctxDe(r, memoria), buscar, proxy: null, agora: () => relogio };
  const raiz = document.createElement("div");
  const caixa = noticias(raiz, ctx);
  await caixa.pronto;
  assert.equal(caixa.estado(), "ok");
  const feitas = quantas;
  await caixa.atualizar();
  assert.equal(quantas, feitas, "dentro do prazo de 15 min não recarrega");
  relogio += 16 * 60000; cair = true;
  await caixa.atualizar();
  assert.equal(caixa.estado(), "erro");
  assert.match(raiz.textContent, /cópia guardada/);
  assert.ok(achar(raiz, (n) => n.tag === "a").length > 0);
  caixa.parar();
  const sozinha = document.createElement("div");
  const sem = noticias(sozinha, { ...ctxDe(r, new Memoria()), buscar: async () => { throw new TypeError("offline"); }, proxy: null });
  await sem.pronto;
  assert.equal(sem.estado(), "erro");
  assert.match(sozinha.textContent, /Não consegui carregar[\s\S]*tentar de novo/);
  sem.parar();
  const c2 = document.createElement("div"), vazia = clima(c2, ctxDe(r, new Memoria()));
  await vazia.pronto;
  assert.equal(vazia.estado(), "vazio");
  assert.match(c2.textContent, /Informe a sua cidade/);
  vazia.parar();
});

test("caixas de clima e vagas: dados reais simulados, link de vaga seguro, título de vaga com HTML vira texto", async () => {
  const r = rede(), memoria = new Memoria();
  await memoria.definirMeta("cidade", "fortaleza");
  const c1 = document.createElement("div"), cx = clima(c1, ctxDe(r, memoria));
  await cx.pronto;
  assert.equal(cx.estado(), "ok");
  assert.match(c1.textContent, /30°C · parcialmente nublado[\s\S]*Fortaleza, Ceará[\s\S]*máxima de 31°C[\s\S]*Chance de chuva: 40%/);
  cx.parar();
  const c2 = document.createElement("div"), cv = vagas(c2, ctxDe(r, memoria));
  await cv.pronto;
  assert.equal(cv.estado(), "ok");
  assert.match(c2.textContent, /Dev Python/);
  assert.ok(!/onerror|<img/.test(c2.textContent) || !achar(c2, (n) => n.tag === "img").length);
  assert.match(c2.textContent, /diga "minha stack é/i);
  cv.parar();
  const semRede = document.createElement("div"), v2 = vagas(semRede, { ...ctxDe(r, new Memoria()), buscar: async () => { throw new TypeError("offline"); } });
  await v2.pronto;
  assert.equal(v2.estado(), "erro");
  v2.parar();
  const t = document.createElement("div"), tc = tecnologia(t, ctxDe(r, new Memoria()));
  await tc.pronto;
  assert.match(t.textContent, /Notícias de tecnologia[\s\S]*Hacker News/);
  tc.parar();
});

test("chat: notícias numeradas, ler notícia N, notícias de assunto, radar nicho/ajuda, parar/continuar", async () => {
  const r = rede(), memoria = new Memoria();
  const falas = [];
  const fala = { ditas: falas, disponivel: () => true, esperar: async () => {}, falar: async (t) => { falas.push(t); }, parar() {}, manterAcesa: async () => {} };
  const ctx = criarContexto({ memoria, nuvem: { brave: async () => ({ base: BASE }), armazem: {} }, buscar: r.buscar, fala });
  const motor = new Motor({ saber, memoria, buscar: r.buscar, agora: () => new Date("2026-10-21T09:00:00") });
  motor.noticiasCtx = ctx;
  assert.match(await motor.responder("notícias"), /1\. .* — .* https:\/\//);
  assert.match(await motor.responder("Jarvis, notícias de tecnologia"), /Manchetes \(tecnologia\):/);
  assert.match(await motor.responder("notícias do Brasil"), /Notícias sobre brasil|Fora do ar|Não consegui/);
  assert.match(await motor.responder("notícias de tecnologia"), /Diga "ler notícia 1"/);
  assert.match(await motor.responder("ler notícia 99"), /A lista tem \d+ notícias/);
  assert.match(await motor.responder("ler notícia 1 completa"), /Lendo a notícia 1: .*\(artigo completo\)/);
  await ctx.leitor.fim();
  assert.ok(falas.length >= 1 && falas.join(" ").includes("Texto do artigo"));
  assert.match(await motor.responder("radar"), /Defina o nicho do Radar/);
  assert.match(await motor.responder("radar nicho inteligência artificial"), /Nicho do Radar: \*\*inteligência artificial\*\*/);
  assert.match(await motor.responder("radar ajuda"), /radar nicho/);
  assert.match(await motor.responder("radar ia ligar"), /Radar com IA ligado/);
  assert.match(await motor.responder("ouvir radar"), /Ainda não montei o radar/);
  assert.match(await motor.responder("parar"), /Não estou lendo nada/);
  assert.match(await motor.responder("continuar"), /nenhuma leitura parada/);
  const semCtx = new Motor({ saber, memoria: new Memoria(), buscar: r.buscar });
  assert.match(await semCtx.responder("ler notícia 1"), /não estão ligadas/);
  assert.match(await semCtx.responder("notícias"), /Manchetes|Não consegui/);
});
