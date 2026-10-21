// A resposta do PC pareado é dado de terceiros (o PC pode estar comprometido, a rede pode adulterar ou o cache pode estar corrompido).
// Aqui cada rota é reconstruída só com os campos esperados, com tipo e tamanho conferidos. Formato errado => null (o chamador cai no cache).
const simples = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const txt = (v, max) => (typeof v === "string" ? v.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "").slice(0, max) : "");
const num = (v) => (Number.isFinite(v) && v >= 0 ? Math.min(v, 1e9) : 0);
const data = (v) => (typeof v === "string" && v.length <= 40 && !Number.isNaN(Date.parse(v)) ? v : null);
const lista = (v, max) => (Array.isArray(v) ? v.slice(0, max) : []);

function evento(e) {
  if (!simples(e)) return null;
  const inicio = data(e.inicio);
  if (!inicio) return null;
  return { titulo: txt(e.titulo, 200) || "(sem título)", inicio, fim: data(e.fim) || inicio, dia_inteiro: e.dia_inteiro === true, local: txt(e.local, 200), suspeito: e.suspeito === true };
}
const eventos = (v, max) => lista(v, max).map(evento).filter(Boolean);

function agenda(d) {
  if (d.sem_agendas === true) return { sem_agendas: true, avisos: [], hoje: [], semana: [], proximo: null };
  return { sem_agendas: false, avisos: lista(d.avisos, 10).map((a) => txt(a, 200)), hoje: eventos(d.hoje, 100), semana: eventos(d.semana, 300), proximo: evento(d.proximo) };
}

function emails(d) {
  if (d.sem_contas === true) return { sem_contas: true };
  if (!simples(d.contagem) || !simples(d.baldes)) return null;
  const balde = (l) => lista(l, 50).filter(simples).map((m) => ({ de: txt(m.de, 120), assunto: txt(m.assunto, 300), resumo: txt(m.resumo, 500) }));
  const c = d.contagem;
  return { sem_contas: false, contagem: { acao: num(c.acao), info: num(c.info), ruido: num(c.ruido), suspeito: num(c.suspeito) }, baldes: { acao: balde(d.baldes.acao), info: balde(d.baldes.info), ruido: balde(d.baldes.ruido) } };
}

const ROTAS = {
  agenda, emails,
  briefing: (d) => (typeof d.texto === "string" ? { texto: txt(d.texto, 8000) } : null),
  agentes: (d) => (JSON.stringify(d).length <= 200_000 ? d : null),
};

// Devolve os dados limpos ou null se o formato não for o esperado.
export function validarResposta(rota, dados) {
  if (!simples(dados) || !ROTAS[rota]) return null;
  try { return ROTAS[rota](dados); } catch { return null; }
}
