// Informações do dia pela internet, direto do celular: clima (Open-Meteo), notícias (feeds via rss2json e Hacker News) e vagas
// (GitHub e Remotive). Só fontes que o navegador aceita (CORS); só leitura; nunca se candidata a nada.
import { fold } from "./util.js";

const WMO = { 0: "céu limpo", 1: "predomínio de sol", 2: "parcialmente nublado", 3: "nublado", 45: "neblina", 48: "neblina com geada", 51: "garoa fraca", 53: "garoa", 55: "garoa forte",
  61: "chuva fraca", 63: "chuva", 65: "chuva forte", 66: "chuva congelante", 67: "chuva congelante forte", 71: "neve fraca", 73: "neve", 75: "neve forte", 80: "pancadas de chuva fracas",
  81: "pancadas de chuva", 82: "pancadas de chuva fortes", 95: "trovoadas", 96: "trovoadas com granizo", 99: "trovoadas fortes com granizo" };

async function json(buscar, url) {
  const r = await buscar(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// ── clima ───────────────────────────────────────────────────────────────
export async function clima(cidade, buscar = (...a) => fetch(...a)) {
  if (!cidade) return 'Em que cidade? Diga "clima em Fortaleza" ou "minha cidade é Fortaleza" para eu lembrar.';
  const geo = (p) => json(buscar, `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cidade)}&count=1&language=pt${p}`);
  let lugar = (await geo("&countryCode=BR")).results?.[0] || (await geo("")).results?.[0];
  if (!lugar) return `Não achei a cidade "${cidade}".`;
  const d = await json(buscar, `https://api.open-meteo.com/v1/forecast?latitude=${lugar.latitude}&longitude=${lugar.longitude}&timezone=auto&forecast_days=1`
    + "&current=temperature_2m,apparent_temperature,relative_humidity_2m,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code");
  const agora = d.current || {}, dia = d.daily || {};
  const nome = [lugar.name, lugar.admin1].filter(Boolean).join(", ");
  const chuva = (dia.precipitation_probability_max || [null])[0];
  return `Em ${nome} agora faz ${Math.round(agora.temperature_2m)}°C, ${WMO[agora.weather_code] || "tempo indefinido"}, com sensação de ${Math.round(agora.apparent_temperature)}°C. `
    + `Hoje a máxima é ${Math.round(dia.temperature_2m_max[0])}°C e a mínima ${Math.round(dia.temperature_2m_min[0])}°C` + (chuva != null ? `, com ${chuva}% de chance de chuva` : "") + ".";
}

// ── notícias ────────────────────────────────────────────────────────────
export const FEEDS = {
  gerais: { G1: "https://g1.globo.com/rss/g1/", "BBC Brasil": "https://feeds.bbci.co.uk/portuguese/rss.xml", "Agência Brasil": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml" },
  tecnologia: { Tecnoblog: "https://tecnoblog.net/feed/", Canaltech: "https://canaltech.com.br/rss/", "Olhar Digital": "https://olhardigital.com.br/feed/" },
};

export async function noticias(tipo = "gerais", limite = 5, buscar = (...a) => fetch(...a)) {
  const porFonte = {}, avisos = [];
  await Promise.all(Object.entries(FEEDS[tipo] || FEEDS.gerais).map(async ([nome, url]) => {
    try {
      const d = await json(buscar, `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(url)}`);
      porFonte[nome] = (d.items || []).map((i) => ({ fonte: nome, titulo: String(i.title || "").trim(), link: i.link, quando: Date.parse(String(i.pubDate || "").replace(" ", "T") + "Z") || 0 }))
        .sort((a, b) => b.quando - a.quando);
    } catch (e) { avisos.push(`${nome}: ${e.message}`); }
  }));
  if (tipo === "tecnologia") {  // Hacker News: manchetes de tecnologia do mundo (em inglês)
    try {
      const ids = (await json(buscar, "https://hacker-news.firebaseio.com/v0/topstories.json")).slice(0, 3);
      porFonte["Hacker News"] = await Promise.all(ids.map(async (id) => { const i = await json(buscar, `https://hacker-news.firebaseio.com/v0/item/${id}.json`); return { fonte: "Hacker News", titulo: i.title, link: i.url || `https://news.ycombinator.com/item?id=${id}`, quando: 0 }; }));
    } catch (e) { avisos.push(`Hacker News: ${e.message}`); }
  }
  const escolhidas = [], vistos = new Set();
  while (escolhidas.length < limite && Object.values(porFonte).some((l) => l.length)) {
    for (const nome of Object.keys(porFonte)) {
      const item = porFonte[nome].shift();
      if (item && escolhidas.length < limite && !vistos.has(item.titulo.toLowerCase().slice(0, 60))) { vistos.add(item.titulo.toLowerCase().slice(0, 60)); escolhidas.push(item); }
    }
  }
  if (!escolhidas.length) return "Não consegui carregar notícias agora" + (avisos.length ? ` (${avisos.join("; ")})` : "") + ".";
  return `**Manchetes (${tipo}):**\n` + escolhidas.map((n) => `- ${n.titulo} — ${n.fonte} ${n.link}`).join("\n") + (avisos.length ? `\n\n_Fora do ar: ${avisos.join("; ")}_` : "");
}

// ── perfil e vagas ──────────────────────────────────────────────────────
const CAMPOS = { stack: "stack", nivel: "nível", modalidade: "modalidade", ingles: "inglês", cidade: "cidade", evitar: "evitar" };
const REPOS = ["frontendbr/vagas", "backend-br/vagas", "react-brasil/vagas"];

export async function perfil(memoria) {
  const nota = await memoria.ler("Perfil/Dev");
  const dados = {};
  for (const linha of (nota?.corpo || "").split("\n")) { const m = /^(\w+):\s*(.*)$/.exec(linha); if (m) dados[m[1]] = m[2].trim(); }
  return dados;
}

export async function atualizarPerfil(memoria, texto) {
  const baixo = fold(texto).replace(/[?!.]+$/g, "").trim();
  let m = /^(?:meu|minha)\s+(stack|nivel|modalidade|ingles|cidade)\s*(?:e|eh|sao|:|=)\s*(.+)$/.exec(baixo);
  const campo = m ? m[1] : /^(?:quero\s+)?evit\w+\s+(.+)$/.test(baixo) ? "evitar" : null;
  if (!campo) return null;
  const valor = m ? m[2] : /^(?:quero\s+)?evit\w+\s+(.+)$/.exec(baixo)[1];
  const dados = await perfil(memoria);
  dados[campo] = campo === "evitar" && dados.evitar ? `${dados.evitar}, ${valor}` : valor;
  await memoria.guardar("Perfil/Dev", Object.entries(dados).map(([k, v]) => `${k}: ${v}`).join("\n"), "perfil", "Perfil de desenvolvedor");
  if (campo === "cidade") await memoria.definirMeta("cidade", valor);
  return `Anotei: ${CAMPOS[campo]} = ${dados[campo]}.`;
}

const lista = (t) => String(t || "").split(/[,;/]| e /).map((x) => fold(x).trim()).filter(Boolean);

export function pontuar(vaga, p, agora = Date.now()) {
  const texto = fold(`${vaga.titulo} ${vaga.etiquetas} ${vaga.descricao}`);
  let pontos = 0;
  const motivos = [];
  for (const t of lista(p.stack)) if (new RegExp(`(?<![\\p{L}\\p{N}])${t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?![\\p{L}\\p{N}])`, "u").test(texto)) { pontos += 3; motivos.push(`usa ${t}`); }
  for (const t of lista(p.evitar)) if (texto.includes(t)) { pontos -= 5; motivos.push(`tem ${t} (você evita)`); }
  if (/remot/.test(fold(p.modalidade || "")) && /remot|home ?office|anywhere/.test(texto)) { pontos += 2; motivos.push("remota"); }
  if (p.nivel && texto.includes(fold(p.nivel))) { pontos += 1; motivos.push(`nível ${p.nivel}`); }
  if (vaga.quando && agora - vaga.quando < 14 * 86400000) { pontos += 1; motivos.push("recente"); }
  return [pontos, motivos];
}

export async function coletarVagas(buscar = (...a) => fetch(...a)) {
  const vagas = [], avisos = [];
  await Promise.all([
    ...REPOS.map(async (repo) => {
      try {
        for (const i of await json(buscar, `https://api.github.com/repos/${repo}/issues?state=open&per_page=30`)) {
          if (!i.pull_request) vagas.push({ titulo: i.title, etiquetas: (i.labels || []).map((l) => l.name).join(" "), descricao: String(i.body || "").slice(0, 600), link: i.html_url, fonte: repo, quando: Date.parse(i.created_at) || 0 });
        }
      } catch (e) { avisos.push(`${repo}: ${e.message}`); }
    }),
    (async () => {
      try {
        for (const j of (await json(buscar, "https://remotive.com/api/remote-jobs?category=software-dev&limit=60")).jobs || []) {
          vagas.push({ titulo: j.title, etiquetas: (j.tags || []).join(" "), descricao: `${j.company_name} ${String(j.description || "").replace(/<[^>]+>/g, " ").slice(0, 500)}`, link: j.url, fonte: "Remotive (vagas remotas)", quando: Date.parse(j.publication_date) || 0 });
        }
      } catch (e) { avisos.push(`Remotive: ${e.message}`); }
    })(),
  ]);
  return { vagas, avisos };
}

export async function vagas(memoria, buscar) {
  const p = await perfil(memoria);
  if (!p.stack) return 'Para achar vagas que combinam com você, diga a sua stack: "minha stack é Python e React". Também ajudam "meu nível é pleno", "minha modalidade é remoto" e "quero evitar PHP".';
  const { vagas: todas, avisos } = await coletarVagas(buscar);
  const boas = todas.map((v) => [...pontuar(v, p), v]).filter(([pts]) => pts > 0).sort((a, b) => b[0] - a[0]).slice(0, 8);
  if (!boas.length) return "Não achei vagas que combinam com o seu perfil agora" + (avisos.length ? ` (fora do ar: ${avisos.join("; ")})` : "") + ".";
  return "**Vagas que combinam com você** (fontes públicas; eu nunca me candidato por você):\n"
    + boas.map(([, motivos, v]) => `- **${v.titulo}** — ${v.fonte}\n  ${motivos.join(", ")}\n  ${v.link}`).join("\n") + (avisos.length ? `\n\n_Fora do ar: ${avisos.join("; ")}_` : "");
}
