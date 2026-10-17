// O que o PC faz, o celular também faz: habilidades, revisão, stack, clima, notícias, vagas, perfil e projetos.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { atualizarPerfil, clima, coletarVagas, noticias, perfil, pontuar, vagas } from "../js/info.js";
import { Memoria } from "../js/memoria.js";
import { Motor } from "../js/motor.js";
import { revisar, relatorio } from "../js/revisao.js";
import { Saber } from "../js/saber.js";

const dados = JSON.parse(readFileSync(new URL("../dados/saber.json", import.meta.url), "utf8"));
const saber = new Saber(dados);
const resposta = (corpo, status = 200) => ({ ok: status < 400, status, json: async () => corpo });
const relogio = () => new Date("2026-10-19T10:00:00");
const motor = (buscar) => new Motor({ saber, memoria: new Memoria(undefined, relogio), buscar, agora: relogio });

test("habilidades: as 23 do PC, checklist, plano e treino da semana em rodízio", () => {
  const m = motor();
  assert.equal(m.habil.catalogo.length, 23);
  assert.match(m.habil.checklist("segurança"), /- \[ \] Consultas parametrizadas[\s\S]*iniciante/);
  assert.match(m.habil.plano("testes"), /Plano para evoluir: Testes automatizados[\s\S]*Treino da semana/);
  assert.match(m.habil.checklist("culinária"), /Não conheço esse aspecto/);
  const titulos = new Set(Array.from({ length: 23 }, (_, i) => m.habil.treinoDaSemana(new Date(2026, 0, 5 + 7 * i)).split("\n")[0]));
  assert.equal(titulos.size, 23);  // uma habilidade diferente por semana, nas 23
});

test("revisão de código e de diffs com as mesmas regras do PC", () => {
  const chave = "AKIA" + "ABCDEFGHIJKLMNOP";
  const diff = `diff --git a/app/api.py b/app/api.py\n--- a/app/api.py\n+++ b/app/api.py\n@@ -10,3 +10,9 @@ def listar():\n     contexto = 1\n-    antigo = "removido com ev${"al"}(x)"\n`
    + `+    resultado = ev${"al"}(pedido)\n+    db.execute(f"SELECT * FROM clientes WHERE nome = '{nome}'")\n+    subprocess.run(cmd, shell=True)\n+    try:\n+        gravar()\n+    except:\n+        pass\n`
    + `+    chave = "${chave}"\n+    print("depurando")  # TODO limpar\n`;
  const { achados } = revisar(diff);
  const regras = new Set(achados.map((a) => a.regra));
  for (const esperada of ["Execução de código dinâmico", "SQL montado com texto", "Comando de shell montado como texto", "Exceção engolida", "Possível segredo no código", "Pendência marcada", "Saída de depuração", "Código alterado sem teste"]) assert.ok(regras.has(esperada), esperada);
  const ev = achados.find((a) => a.regra === "Execução de código dinâmico");
  assert.deepEqual([ev.arquivo, ev.linha, ev.gravidade], ["app/api.py", 11, "alta"]);
  assert.ok(!achados.some((a) => a.trecho.includes("removido")) && achados.every((a) => !a.trecho.includes(chave)));
  assert.match(relatorio("x = 1\n"), /Não achei problemas/);
});

test("stack: recomendar, comparar e descrever como o PC", async () => {
  const m = motor();
  assert.match(m.stack.recomendar("loja virtual"), /Para loja virtual \/ e-commerce, eu recomendo:[\s\S]*Back-end/);
  assert.match(m.stack.recomendar("coisa estranha"), /Não entendi que tipo de sistema/);
  assert.match(await m.responder("qual stack para uma loja virtual"), /eu recomendo/);
  assert.match(await m.responder("quais linguagens para back end"), /Back end: o que eu conheço/);
  assert.match(await m.responder("compare React e Vue"), /React × Vue[\s\S]*Pontos fortes/);
  assert.match(await m.responder("o que é React"), /Como começar/);
});

test("clima, notícias e vagas pela internet (fontes simuladas) e perfil/projetos pela memória", async () => {
  const buscar = async (url) => {
    if (url.includes("geocoding")) return resposta({ results: [{ name: "Fortaleza", admin1: "Ceará", latitude: -3.7, longitude: -38.5 }] });
    if (url.includes("api.open-meteo")) return resposta({ current: { temperature_2m: 29.6, apparent_temperature: 33.2, weather_code: 2 }, daily: { temperature_2m_max: [31.4], temperature_2m_min: [25.1], precipitation_probability_max: [40] } });
    if (url.includes("rss2json")) return resposta({ items: [{ title: `Manchete de ${decodeURIComponent(url).includes("tecnoblog") ? "Tecnoblog" : "teste"}`, link: "https://x.org/1", pubDate: "2026-10-19 08:00:00" }] });
    if (url.includes("hacker-news") && url.endsWith("topstories.json")) return resposta([1, 2, 3]);
    if (url.includes("hacker-news")) return resposta({ title: "Show HN: algo", url: "https://hn.example/1" });
    if (url.includes("api.github.com")) return resposta([{ title: "Vaga Desenvolvedor Python Pleno - Remoto", labels: [{ name: "Python" }, { name: "Remoto" }], body: "Django, FastAPI", html_url: "https://github.com/x/vagas/issues/1", created_at: "2026-10-15T10:00:00Z" },
      { title: "Vaga PHP Júnior", labels: [{ name: "PHP" }], body: "", html_url: "https://github.com/x/vagas/issues/2", created_at: "2026-10-01T10:00:00Z" }]);
    if (url.includes("remotive")) return resposta({ jobs: [{ title: "Python Engineer", tags: ["python"], company_name: "Acme", description: "<p>Remote</p>", url: "https://remotive.com/1", publication_date: "2026-10-18T00:00:00" }] });
    return resposta({}, 404);
  };
  const m = motor(buscar);
  assert.match(await m.responder("clima em Fortaleza"), /Em Fortaleza, Ceará agora faz 30°C, parcialmente nublado, com sensação de 33°C\. Hoje a máxima é 31°C e a mínima 25°C, com 40% de chance de chuva\./);
  assert.match(await clima("", buscar), /Em que cidade/);
  assert.match(await m.responder("minha cidade é Fortaleza"), /cidade = fortaleza/);
  assert.match(await m.responder("como está o clima"), /Em Fortaleza/);
  assert.match(await m.responder("notícias de tecnologia"), /Manchetes \(tecnologia\)[\s\S]*Hacker News/);
  assert.match(await m.responder("vagas"), /diga a sua stack/);
  await m.responder("minha stack é Python e React");
  await m.responder("meu nível é pleno");
  await m.responder("minha modalidade é remoto");
  await m.responder("quero evitar PHP");
  assert.deepEqual(await perfil(m.memoria), { stack: "python e react", nivel: "pleno", modalidade: "remoto", cidade: "fortaleza", evitar: "php" });
  const lista = await m.responder("quais vagas tem para mim");
  assert.match(lista, /Vaga Desenvolvedor Python Pleno[\s\S]*usa python/);
  assert.ok(!lista.includes("Vaga PHP Júnior"));  // o que o usuário evita não aparece
  assert.match(lista, /eu nunca me candidato/);
  const { vagas: todas } = await coletarVagas(buscar);
  assert.equal(todas.length, 7);  // 3 repositórios × 2 vagas + 1 do Remotive
  assert.ok(pontuar(todas[0], await perfil(m.memoria))[0] > pontuar(todas[1], await perfil(m.memoria))[0]);
});

test("projetos: anotar, ficha e lista; revisão pelo chat; evoluir e checklist", async () => {
  const m = motor();
  assert.match(await m.responder("meus projetos"), /Nenhum projeto ainda/);
  assert.match(await m.responder("anota no projeto Loja que o banco é PostgreSQL"), /Anotado no projeto \*\*Loja\*\*/);
  await m.responder("anota no projeto Loja que o front é React");
  assert.match(await m.responder("ficha do projeto Loja"), /PostgreSQL[\s\S]*React/);
  assert.match(await m.responder("meus projetos"), /Loja/);
  assert.match(await m.responder("revise este trecho\nx = ev" + "al(y)"), /Execução de código dinâmico/);
  assert.match(await m.responder("revise este trecho"), /Cole o diff/);
  assert.match(await m.responder("quais habilidades de programador"), /Habilidades de programador que eu acompanho/);
  assert.match(await m.responder("treino da semana"), /Treino da semana/);
  assert.match(await m.responder("checklist de segurança"), /Checklist: Segurança/);
});

test("falhas da internet não derrubam nada", async () => {
  const caiu = async () => { throw new TypeError("Failed to fetch"); };
  const m = motor(caiu);
  assert.match(await m.responder("clima em Recife"), /Não consegui ver o clima/);
  assert.match(await m.responder("notícias"), /Não consegui carregar notícias/);
  await atualizarPerfil(m.memoria, "minha stack é Go");
  assert.match(await vagas(m.memoria, caiu), /Não achei vagas.*fora do ar/);
});
