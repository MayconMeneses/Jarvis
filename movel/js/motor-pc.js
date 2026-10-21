import { marca, textoRadar, textoSessoes, textoTarefas, textoUso, textoVitais } from "./pc-texto.js";
// Pedidos de conversa que dependem do PC pareado: agenda, próximo compromisso, e-mails e bom dia. O objeto `pc` (PcPareado) é ligado pelo main.js.
// Tudo o que vem do PC é texto de terceiros: só vira texto na tela, nunca instrução.
const EXTRAS = [
  ["pc_agenda", /^(minha agenda( de hoje| da semana)?|agenda( de hoje| da semana)?|o que (eu )?tenho (hoje|na agenda)|meus compromissos)$/],
  ["pc_proximo", /^((qual (e )?)?(o )?(meu )?proximo compromisso|proximo compromisso)$/],
  ["pc_emails", /^((meus?|os) )?e-?mails?( importantes| de acao| novos)?$|^tenho e-?mails?( novos| importantes)?$/],
  ["pc_bomdia", /^(bom dia|boa tarde|boa noite)$/],
  ["pc_vitais", /^(como (esta|anda) (o )?(meu )?(pc|computador)|vitais( do pc)?|saude do pc|(cpu|ram|memoria|disco) do pc)$/],
  ["pc_sessoes", /^((minhas )?sessoes( do claude( code)?)?|sessoes do claude( code)?|tem (algum )?claude (esperando|precisando de mim))$/],
  ["pc_uso", /^(minha cota|cota( do claude)?|uso do claude|quanto (falta|sobra) (da|na) (minha )?cota)$/],
  ["pc_tarefas", /^(minhas )?tarefas (do pc|de codigo)$/],
  ["pc_radar", /^(radar|boletim) do pc$/],
];
const PRECISA = "Isso precisa do PC pareado (opcional): na aba Cérebro, em \"PC pareado\", informe o endereço do PC e o código da janela dele. Sem o PC eu não vejo agenda, e-mails, vitais, sessões nem cota.";
const hora = (iso) => new Date(iso).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
const dia = (iso) => new Date(iso).toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "2-digit" });
const quando = (e, comDia) => (e.dia_inteiro ? "dia inteiro" : hora(e.inicio)) + (comDia ? `, ${dia(e.inicio)}` : "");
const linha = (e, comDia = false) => `- ${quando(e, comDia)}: ${e.titulo}${e.local ? ` (${e.local})` : ""}`;
export { marca };

export function textoAgenda(r) {
  const a = r.dados;
  if (a.sem_agendas) return "O PC ainda não tem agenda conectada.";
  const hoje = a.hoje.length ? `**Hoje (${a.hoje.length}):**\n` + a.hoje.map((e) => linha(e)).join("\n") : "Nenhum compromisso hoje.";
  const resto = a.semana.filter((e) => !a.hoje.some((h) => h.inicio === e.inicio && h.titulo === e.titulo));
  return hoje + (resto.length ? "\n\n**Próximos 7 dias:**\n" + resto.slice(0, 12).map((e) => linha(e, true)).join("\n") : "") + marca(r);
}

export function textoEmails(r) {
  const e = r.dados;
  if (e.sem_contas) return "O PC ainda não tem conta de e-mail conectada.";
  const c = e.contagem, itens = (l) => l.map((m) => `- ${m.de}: ${m.assunto}`).join("\n");
  let t = `**E-mails não lidos:** ${c.acao} de ação, ${c.info} informativos, ${c.ruido} ruído${c.suspeito ? `, ${c.suspeito} suspeitos (omitidos)` : ""}.`;
  if (e.baldes.acao.length) t += "\n**Pedem ação:**\n" + itens(e.baldes.acao);
  if (e.baldes.info.length) t += "\n**Informativos:**\n" + itens(e.baldes.info.slice(0, 5));
  return t + marca(r);
}

// Pedido de leitura simples: sem PC pareado explica; com PC mostra o texto (ou o aviso amigável / a cópia datada).
const leitura = (rota, formatar) => async function () {
  if (!this.pc || !(await this.pc.pareado())) return PRECISA;
  const r = await this.pc.obter(rota);
  return r.ok ? formatar(r) : r.erro;
};

const HANDLERS = {
  _pc_vitais: leitura("vitais", textoVitais), _pc_sessoes: leitura("sessoes", textoSessoes), _pc_uso: leitura("uso", textoUso),
  _pc_tarefas: leitura("tarefas", textoTarefas), _pc_radar: leitura("radar", textoRadar),
  async _pc_agenda() {
    if (!this.pc || !(await this.pc.pareado())) return PRECISA;
    const r = await this.pc.obter("agenda");
    return r.ok ? textoAgenda(r) : r.erro;
  },
  async _pc_proximo() {
    if (!this.pc || !(await this.pc.pareado())) return PRECISA;
    const r = await this.pc.obter("agenda");
    if (!r.ok) return r.erro;
    return (r.dados.proximo ? "**Próximo compromisso:**\n" + linha(r.dados.proximo, true) : "Sem próximo compromisso nos próximos dias.") + marca(r);
  },
  async _pc_emails() {
    if (!this.pc || !(await this.pc.pareado())) return PRECISA;
    const r = await this.pc.obter("emails");
    return r.ok ? textoEmails(r) : r.erro;
  },
  // Sem PC pareado devolve null: o "bom dia" local de sempre (aviso ao abrir o app, conversa normal) continua como está.
  async _pc_bomdia() {
    if (!this.pc || !(await this.pc.pareado())) return null;
    const r = await this.pc.obter("briefing");
    return r.ok ? String(r.dados.texto) + marca(r) : null;
  },
};

export function instalarPc(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}
