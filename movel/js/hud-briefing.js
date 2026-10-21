// Texto do cartão central do HUD (sobre o orbe): saudação local e resumos de AGENDA, E-MAILS e NOTÍCIAS. Funções PURAS: recebem dados já lidos
// (do PC pareado, das notas ou da última lista de notícias) e devolvem { titulo, linhas }. Tudo isso é texto de terceiros: quem desenha usa textContent.
export const ABAS = [{ id: "agenda", rotulo: "AGENDA" }, { id: "emails", rotulo: "E-MAILS" }, { id: "noticias", rotulo: "NOTÍCIAS" }];

export function saudacao(hora, nome = "") {
  const g = hora < 12 ? "Bom dia" : hora < 18 ? "Boa tarde" : "Boa noite";
  return nome ? `${g}, ${nome}` : g;
}

const corta = (t, n = 46) => { const s = String(t ?? "").replace(/\s+/g, " ").trim(); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
const plural = (n, um, varios) => `${n} ${n === 1 ? um : varios}`;
const hhmm = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }); };

// dados do PC: { sem_agendas, hoje: [{ inicio, titulo, dia_inteiro }] }; lembretes: textos locais de hoje.
export function resumoAgenda(dados, lembretes = []) {
  const hoje = Array.isArray(dados?.hoje) ? dados.hoje : [];
  const linhas = hoje.slice(0, 2).map((e) => `${e.dia_inteiro ? "dia todo" : hhmm(e.inicio)} ${corta(e.titulo, 30)}`.trim());
  if (hoje.length) return { titulo: plural(hoje.length, "compromisso hoje", "compromissos hoje"), linhas };
  if (lembretes.length) return { titulo: plural(lembretes.length, "lembrete hoje", "lembretes hoje"), linhas: lembretes.slice(0, 2).map((t) => corta(t, 36)) };
  if (dados && !dados.sem_agendas) return { titulo: "Nada na agenda hoje", linhas: [] };
  return { titulo: "Agenda sem PC", linhas: [dados ? "O PC não tem agenda conectada." : "Pareie o PC na aba Cérebro."] };
}

export function resumoEmails(dados) {
  const c = dados?.contagem;
  if (!c) return { titulo: "E-mails sem PC", linhas: [dados?.sem_contas ? "O PC não tem conta de e-mail." : "Pareie o PC na aba Cérebro."] };
  const total = (c.acao || 0) + (c.info || 0);
  if (!total) return { titulo: "Caixa em dia", linhas: c.suspeito ? [plural(c.suspeito, "suspeito omitido", "suspeitos omitidos")] : [] };
  return { titulo: plural(c.acao || 0, "pede ação", "pedem ação"), linhas: [`${c.info || 0} informativos`, ...(c.suspeito ? [plural(c.suspeito, "suspeito omitido", "suspeitos omitidos")] : [])] };
}

export function resumoNoticias(itens) {
  const lista = Array.isArray(itens) ? itens : [];
  if (!lista.length) return { titulo: "Notícias", linhas: ["Carregando as manchetes…"] };
  return { titulo: plural(lista.length, "manchete", "manchetes"), linhas: lista.slice(0, 2).map((n) => corta(n.titulo, 40)) };
}

// Setas trocam de aba do cartão (circular); Home/End vão às pontas. Outra tecla não faz nada (null).
export function proximaAba(atual, tecla, ids = ABAS.map((a) => a.id)) {
  const i = ids.indexOf(atual);
  if (tecla === "ArrowRight") return ids[(i + 1) % ids.length];
  if (tecla === "ArrowLeft") return ids[(i - 1 + ids.length) % ids.length];
  if (tecla === "Home") return ids[0];
  if (tecla === "End") return ids[ids.length - 1];
  return null;
}

// Lembretes que vencem hoje (notas "Lembretes/..." com a linha "Para: AAAA-MM-DD"): a "agenda" local quando não há PC pareado.
export function lembretesDeHoje(notas, hoje) {
  const saida = [];
  for (const n of Array.isArray(notas) ? notas : []) {
    const para = /^Para: (\d{4}-\d{2}-\d{2})/m.exec(String(n?.corpo ?? ""))?.[1];
    if (para && para <= hoje) saida.push(String(n.corpo).split("\n").slice(1).join(" ").trim() || String(n.titulo || "Lembrete"));
  }
  return saida;
}
