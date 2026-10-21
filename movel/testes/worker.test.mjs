// Worker da Cloudflare (movel/proxy/nvidia-worker.js, gerado por montar.mjs): segurança das rotas /rss, /ler, /ical, /saude e regressão das rotas NVIDIA/Brave.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { montar } from "../proxy/montar.mjs";
import { buscarSeguro } from "../proxy/fonte/buscar.js";
import { extrairTexto } from "../proxy/fonte/texto.js";
import { validarUrl } from "../proxy/fonte/seguranca.js";

const { default: worker } = await import("../proxy/nvidia-worker.js");
const ORIGEM = "https://mayconmeneses.github.io";
let ipSeq = 0;
const novoIp = () => `203.0.113.${++ipSeq}`;

// fetch falso: mapa url -> resposta (ou função). Guarda o que foi pedido ao "destino".
function falso(mapa) {
  const chamadas = [];
  globalThis.fetch = async (url, init = {}) => {
    chamadas.push({ url: String(url), init });
    const r = mapa[String(url)];
    if (!r) throw new Error("rede indisponível");
    return typeof r === "function" ? r(init) : r.clone();
  };
  return chamadas;
}
const resp = (corpo, tipo, status = 200, extra = {}) => new Response(corpo, { status, headers: { "Content-Type": tipo, ...extra } });
const pedir = (rota, alvo, cab = {}, metodo = "GET") => worker.fetch(new Request(`https://proxy.exemplo.workers.dev/${rota}${alvo === undefined ? "" : "?url=" + encodeURIComponent(alvo)}`, { method: metodo, headers: { Origin: ORIGEM, "cf-connecting-ip": novoIp(), ...cab } }));
const FEED = '<?xml version="1.0"?><rss version="2.0"><channel><title>Notícias</title><item><title>A</title></item></channel></rss>';

test("/saude lista as rotas sem exigir Origin e só dá CORS à origem certa", async () => {
  const sem = await worker.fetch(new Request("https://p.workers.dev/saude"));
  assert.equal(sem.status, 200);
  const j = await sem.json();
  assert.deepEqual(j.rotas.slice(0, 3), ["rss", "ler", "ical"]);
  assert.equal(sem.headers.get("Access-Control-Allow-Origin"), null);
  const com = await worker.fetch(new Request("https://p.workers.dev/saude", { headers: { Origin: ORIGEM } }));
  assert.equal(com.headers.get("Access-Control-Allow-Origin"), ORIGEM);
});

test("Origin obrigatório e preflight estrito nas rotas novas", async () => {
  const chamadas = falso({ "https://exemplo.com/feed": resp(FEED, "application/xml") });
  for (const cab of [{ Origin: "https://outro-site.com" }, { Origin: ORIGEM + ".evil.com" }, { Origin: "null" }, { Origin: "" }]) {
    const r = await pedir("rss", "https://exemplo.com/feed", cab);
    assert.equal(r.status, 403);
    assert.equal(r.headers.get("Access-Control-Allow-Origin"), null);
  }
  assert.equal((await worker.fetch(new Request("https://p.workers.dev/rss?url=https%3A%2F%2Fexemplo.com%2Ffeed"))).status, 403);
  assert.equal(chamadas.length, 0);
  const ruim = await worker.fetch(new Request("https://p.workers.dev/rss", { method: "OPTIONS", headers: { Origin: "https://outro-site.com" } }));
  assert.equal(ruim.status, 403);
  const bom = await worker.fetch(new Request("https://p.workers.dev/rss", { method: "OPTIONS", headers: { Origin: ORIGEM } }));
  assert.equal(bom.status, 204);
  assert.equal(bom.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.match(bom.headers.get("Access-Control-Allow-Methods"), /GET/);
});

const PROIBIDAS = [
  "http://exemplo.com/feed", "ftp://exemplo.com/a", "file:///etc/passwd", "javascript:alert(1)", "data:text/html,x", "//exemplo.com/a", "exemplo.com/feed", "",
  "https://localhost/a", "https://LOCALHOST./a", "https://app.localhost/a", "https://127.0.0.1/a", "https://127.1/a", "https://2130706433/a", "https://0x7f000001/a", "https://0177.0.0.1/a",
  "https://10.0.0.5/a", "https://192.168.1.1/a", "https://172.16.0.1/a", "https://169.254.169.254/latest/meta-data", "https://0.0.0.0/a", "https://100.64.0.1/a",
  "https://[::1]/a", "https://[::ffff:127.0.0.1]/a", "https://[fe80::1]/a", "https://[fd00::1]/a", "https://[2001:db8::1]/a",
  "https://metadata.google.internal/a", "https://intranet/a", "https://servidor.local/a", "https://roteador.lan/a", "https://127.0.0.1.nip.io/a", "https://localtest.me/a",
  "https://usuario:senha@exemplo.com/a", "https://usuario@exemplo.com/a", "https://exemplo.com:8443/a", "https://exemplo.com:22/a", "https://exemplo.com\\@127.0.0.1/", "https://exemplo.com/a b", "https://exemplo.com/a\nb",
  "https://" + "a".repeat(300) + ".com/", "https://exemplo.com/" + "a".repeat(2100),
];
test("URL proibida (esquema, localhost, IP literal, rede interna, credencial, porta) vira 400 genérico sem tocar na rede", async () => {
  const chamadas = falso({});
  for (const alvo of PROIBIDAS) {
    for (const rota of ["rss", "ler", "ical"]) {
      const r = await pedir(rota, alvo);
      assert.equal(r.status, 400, `${rota} ${alvo}`);
      assert.equal(await r.text(), '{"erro":"endereço não permitido"}');
    }
  }
  assert.equal(chamadas.length, 0);
  for (const r of ["rss", "ler", "ical"]) {
    assert.equal((await pedir(r, undefined)).status, 400);
    const dois = await worker.fetch(new Request(`https://p.workers.dev/${r}?url=https%3A%2F%2Fa.com%2F&url=https%3A%2F%2Fb.com%2F`, { headers: { Origin: ORIGEM, "cf-connecting-ip": novoIp() } }));
    assert.equal(dois.status, 400);
  }
  assert.equal(validarUrl("https://exemplo.com/a#frag").href, "https://exemplo.com/a");
  assert.ok(validarUrl("https://xn--exemplo-9ya.com.br/a"));
});

test("redirecionamento: revalida cada destino, no máximo 3, e nunca chega à rede interna", async () => {
  const para = (u, s = 302) => () => new Response(null, { status: s, headers: { Location: u } });
  const chamadas = falso({
    "https://a.com/interno": para("http://169.254.169.254/latest/meta-data"),
    "https://a.com/local": para("https://localhost/admin"),
    "https://a.com/ip": para("https://10.0.0.1/"),
    "https://a.com/rel": para("//192.168.0.1/x"),
    "https://a.com/http": para("http://b.com/feed"),
    "https://a.com/c1": para("https://a.com/c2"), "https://a.com/c2": para("https://a.com/c3", 301), "https://a.com/c3": para("https://a.com/c4", 307), "https://a.com/c4": para("https://a.com/c5"), "https://a.com/c5": resp(FEED, "application/xml"),
    "https://a.com/ok": para("/destino", 308), "https://a.com/destino": resp(FEED, "application/rss+xml"),
    "https://a.com/vazio": () => new Response(null, { status: 302 }),
  });
  for (const alvo of ["interno", "local", "ip", "rel", "http", "vazio"]) {
    const r = await pedir("rss", "https://a.com/" + alvo);
    assert.equal(r.status, 502, alvo);
    assert.ok(!(await r.text()).includes("a.com"));
  }
  assert.ok(!chamadas.some((c) => /169\.254|localhost|10\.0|192\.168|http:/.test(c.url)));
  assert.ok(chamadas.every((c) => c.init.redirect === "manual"));
  assert.equal((await pedir("rss", "https://a.com/c1")).status, 502);          // 4 redirecionamentos: acima do limite
  assert.equal((await pedir("rss", "https://a.com/ok")).status, 200);          // 1 redirecionamento relativo, revalidado
});

test("não repassa Authorization, cookies nem cabeçalhos do usuário ao destino, nem devolve os do destino", async () => {
  const chamadas = falso({ "https://exemplo.com/feed": resp(FEED, "application/xml", 200, { "Set-Cookie": "sessao=1", "X-Interno": "segredo", Server: "x", "Access-Control-Allow-Origin": "*" }) });
  const r = await pedir("rss", "https://exemplo.com/feed", { Authorization: "Bearer segredo", Cookie: "a=1", "X-Subscription-Token": "tok" });
  assert.equal(r.status, 200);
  assert.deepEqual(Object.keys(chamadas[0].init.headers).sort(), ["accept", "user-agent"]);
  for (const h of ["set-cookie", "x-interno", "server"]) assert.equal(r.headers.get(h), null);
  assert.equal(r.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.equal(r.headers.get("X-Content-Type-Options"), "nosniff");
});

test("/rss devolve o XML cru com application/xml; recusa o que não é feed, tipo errado e erro do destino", async () => {
  const latin = new Uint8Array([...Buffer.from('<?xml version="1.0" encoding="ISO-8859-1"?><rss><title>'), 0xe7, 0xe3, 0x6f, ...Buffer.from("</title></rss>")]);
  falso({
    "https://exemplo.com/feed": resp(FEED, "text/xml; charset=utf-8"),
    "https://exemplo.com/atom": resp('<feed xmlns="http://www.w3.org/2005/Atom"><title>x</title></feed>', "application/atom+xml"),
    "https://exemplo.com/html": resp("<html>oi</html>", "text/html"),
    "https://exemplo.com/falso": resp("<html>oi</html>", "application/xml"),
    "https://exemplo.com/json": resp("{}", "application/json"),
    "https://exemplo.com/404": resp("nada", "text/html", 404),
    "https://exemplo.com/500": resp("erro com segredo", "text/html", 500),
    "https://exemplo.com/latin": resp(latin, "application/xml"),
  });
  const ok = await pedir("rss", "https://exemplo.com/feed");
  assert.equal(ok.status, 200);
  assert.match(ok.headers.get("Content-Type"), /^application\/xml/);
  assert.equal(await ok.text(), FEED);
  assert.equal((await pedir("rss", "https://exemplo.com/atom")).status, 200);
  for (const [alvo, status] of [["html", 415], ["falso", 415], ["json", 415], ["404", 502], ["500", 502]]) assert.equal((await pedir("rss", "https://exemplo.com/" + alvo)).status, status, alvo);
  assert.match(await (await pedir("rss", "https://exemplo.com/latin")).text(), /çã/);
  const falha = await pedir("rss", "https://sem-rede.com/feed");
  assert.equal(falha.status, 502);
  assert.equal(await falha.text(), '{"erro":"falha ao buscar"}');
});

test("/ical devolve o .ics cru e recusa o que não é calendário", async () => {
  const ics = "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n";
  falso({ "https://c.com/a.ics": resp(ics, "text/calendar; charset=utf-8"), "https://c.com/t.ics": resp(ics, "text/plain"), "https://c.com/h": resp("<html>", "text/html"), "https://c.com/x.ics": resp("nao e calendario", "text/calendar") });
  const ok = await pedir("ical", "https://c.com/a.ics");
  assert.equal(await ok.text(), ics);
  assert.match(ok.headers.get("Content-Type"), /^text\/calendar/);
  assert.equal((await pedir("ical", "https://c.com/t.ics")).status, 200);
  assert.equal((await pedir("ical", "https://c.com/h")).status, 415);
  assert.equal((await pedir("ical", "https://c.com/x.ics")).status, 415);
});

test("tamanho: acima de 1,5 MB (declarado ou em fluxo) é recusado com 413", async () => {
  const grande = new Uint8Array(1500001).fill(97);
  falso({
    "https://g.com/declarado": () => new Response(new Uint8Array(10), { status: 200, headers: { "Content-Type": "text/html", "Content-Length": "9999999" } }),
    "https://g.com/fluxo": () => new Response(grande, { status: 200, headers: { "Content-Type": "text/html" } }),
    "https://g.com/limite": () => new Response("<html><body><p>" + "a".repeat(100) + "</p></body></html>", { status: 200, headers: { "Content-Type": "text/html" } }),
  });
  assert.equal((await pedir("ler", "https://g.com/declarado")).status, 413);
  assert.equal((await pedir("ler", "https://g.com/fluxo")).status, 413);
  assert.equal((await pedir("ler", "https://g.com/limite")).status, 200);
});

test("tempo limite: destino que não responde ou não termina o corpo vira 504", async () => {
  const pendente = (init) => new Promise((_, rej) => init.signal.addEventListener("abort", () => rej(new Error("abortado"))));
  const lento = (init) => new Response(new ReadableStream({ start(c) { c.enqueue(new TextEncoder().encode("<rss>")); init.signal.addEventListener("abort", () => c.error(new Error("abortado"))); } }), { status: 200, headers: { "Content-Type": "application/xml" } });
  const url = validarUrl("https://lento.com/feed");
  await assert.rejects(() => buscarSeguro(url, ["application/xml"], { tempoMs: 40, buscar: async (u, i) => pendente(i) }), (e) => e.status === 504);
  await assert.rejects(() => buscarSeguro(url, ["application/xml"], { tempoMs: 40, buscar: async (u, i) => lento(i) }), (e) => e.status === 504);
  await assert.rejects(() => buscarSeguro(url, ["application/xml"], { tempoMs: 40, buscar: () => new Promise(() => {}) }), (e) => e.status === 504);
});

test("/ler: extrai texto limpo, prefere <article>, ignora script/style/nav/footer/form e nunca devolve HTML", async () => {
  const html = `<!doctype html><html lang="pt-BR"><head><title>Título &amp; &lt;b&gt;</title><style>.x{}</style><script>alert("XSS")</script></head>
  <body><nav>Menu Inicio Contato</nav><form><input value="segredo"></form>
  <article><h1>Manchete</h1><p>Primeiro parágrafo com <b>negrito</b> e <script>roubar()</script>texto.</p><p>Segundo&nbsp;parágrafo &#233; &#x41;. ${"palavra ".repeat(60)}</p></article>
  <aside>Anúncio</aside><footer>Rodapé direitos</footer></body></html>`;
  falso({ "https://n.com/a": resp(html, "text/html; charset=utf-8") });
  const r = await pedir("ler", "https://n.com/a");
  assert.equal(r.status, 200);
  assert.match(r.headers.get("Content-Type"), /^application\/json/);
  const j = await r.json();
  assert.deepEqual(Object.keys(j), ["titulo", "texto", "idioma", "url_final", "tamanho"]);
  assert.equal(j.titulo, "Título & <b>");
  assert.equal(j.idioma, "pt");
  assert.equal(j.url_final, "https://n.com/a");
  assert.equal(j.tamanho, Buffer.byteLength(html));
  assert.match(j.texto, /^Manchete\n\nPrimeiro parágrafo com negrito e texto\.\n\nSegundo parágrafo é A\./);
  for (const proibido of ["alert", "roubar", "Menu", "segredo", "Anúncio", "Rodapé", "<p>", "<script"]) assert.ok(!j.texto.includes(proibido), proibido);
});

test("extrairTexto: HTML malicioso não executa, não trava e respeita o limite de 6000", () => {
  const t0 = Date.now();
  const hostis = ["<!--".repeat(300000), "<a ".repeat(300000), "<script>".repeat(100000), "<div>".repeat(200000) + "x", "&".repeat(500000), "&#".repeat(200000), "<".repeat(500000), " ".repeat(1400000) + "\n" + " ".repeat(10), "<nav>".repeat(50000) + "texto".repeat(100)];
  for (const h of hostis) extrairTexto(h);
  assert.ok(Date.now() - t0 < 3000, "demorou demais: " + (Date.now() - t0));
  const e = extrairTexto("<p>" + "é".repeat(9000) + "</p>");
  assert.equal(e.texto.length, 6000);
  assert.equal(e.truncado, true);
  // entidades não são decodificadas duas vezes e tags escapadas ficam como TEXTO inerte
  assert.equal(extrairTexto("<p>&amp;lt;script&amp;gt;</p><p>&lt;img src=x onerror=alert(1)&gt;</p>").texto, "&lt;script&gt;\n\n<img src=x onerror=alert(1)>");
  // nomes de objeto não viram tags/entidades especiais
  assert.equal(extrairTexto("<constructor>a</constructor><__proto__>b</__proto__>&constructor;&toString;").texto, "a<__proto__>b&constructor;&toString;");
  // <nav> sem fechar não engole a página inteira
  assert.match(extrairTexto("<nav>menu<p>Conteúdo importante da página</p>").texto, /Conteúdo importante/);
  // caracteres de controle e de inversão de texto são removidos
  assert.equal(extrairTexto("<p>a‮b\u0000c​d</p>").texto, "abcd");
  assert.equal(extrairTexto("").texto, "");
});

test("método diferente de GET: 405; excesso de pedidos por IP: 429", async () => {
  const chamadas = falso({ "https://exemplo.com/feed": resp(FEED, "application/xml") });
  assert.equal((await pedir("rss", "https://exemplo.com/feed", {}, "POST")).status, 405);
  assert.equal(chamadas.length, 0);
  const ip = { "cf-connecting-ip": "198.51.100.77" };
  const estados = [];
  for (let i = 0; i < 32; i++) estados.push((await pedir("rss", "https://exemplo.com/feed", ip)).status);
  assert.equal(estados.filter((s) => s === 200).length, 30);
  assert.deepEqual(estados.slice(30), [429, 429]);
  assert.equal((await pedir("rss", "https://exemplo.com/feed")).status, 200);   // outro IP não é afetado
});

test("regressão: NVIDIA e Brave continuam iguais (Origin, caminho, repasse só do que precisa)", async () => {
  let repassado;
  globalThis.fetch = async (url, init) => { repassado = { url, init }; return new Response('{"ok":true}', { status: 200, headers: { "Content-Type": "application/json" } }); };
  const req = (m, c, cab = {}, corpo) => new Request("https://p.workers.dev" + c, { method: m, headers: cab, body: corpo });
  assert.equal((await worker.fetch(req("POST", "/v1/chat/completions", { Origin: "https://x.com" }, "{}"))).status, 403);
  assert.equal((await worker.fetch(req("GET", "/admin", { Origin: ORIGEM }))).status, 404);
  assert.equal((await worker.fetch(req("GET", "/rss/", { Origin: ORIGEM }))).status, 404);
  const ok = await worker.fetch(req("POST", "/v1/chat/completions", { Origin: ORIGEM, Authorization: "Bearer nvapi-x", Cookie: "c=1", "Content-Type": "application/json" }, '{"a":1}'));
  assert.equal(ok.status, 200);
  assert.equal(ok.headers.get("Access-Control-Allow-Origin"), ORIGEM);
  assert.equal(repassado.url, "https://integrate.api.nvidia.com/v1/chat/completions");
  assert.deepEqual(repassado.init.headers, { authorization: "Bearer nvapi-x", "content-type": "application/json" });
  assert.equal(repassado.init.body, '{"a":1}');
  await worker.fetch(req("GET", "/brave/res/v1/web/search?q=oi", { Origin: ORIGEM, "X-Subscription-Token": "tok", Authorization: "Bearer nao" }));
  assert.equal(repassado.url, "https://api.search.brave.com/res/v1/web/search?q=oi");
  assert.deepEqual(repassado.init.headers, { "x-subscription-token": "tok", "content-type": "application/json" });
});

test("Cron/Web Push: nada roda por padrão; o arquivo único está em dia com os módulos e dentro das 300 linhas", async () => {
  let rodou = false;
  await worker.scheduled({}, {}, { waitUntil: () => { rodou = true; } });
  await worker.scheduled({}, { JARVIS_CRON: "sim" }, { waitUntil: () => { rodou = true; } });
  assert.equal(rodou, false);
  const gerado = readFileSync(new URL("../proxy/nvidia-worker.js", import.meta.url), "utf8");
  assert.equal(gerado, montar(), "rode: node movel/proxy/montar.mjs");
  assert.ok(gerado.split("\n").length <= 300);
  assert.ok(!/^(import|export (?!default))/m.test(gerado));
});
