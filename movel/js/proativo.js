// Iniciativa própria no celular: ao abrir, a Jarvis lembra do que importa (bom dia, lembretes do dia, tópico do dia, treino da semana).
// Um iPhone não deixa um site acordar sozinho em segundo plano; por isso os avisos aparecem quando o app é aberto.
import { dataPorExtenso, isoData, semanaIso } from "./util.js";

async function umaVez(memoria, chave) {
  if (await memoria.meta("aviso:" + chave)) return false;
  await memoria.definirMeta("aviso:" + chave, true);
  return true;
}

export async function avisos({ memoria, saber, agora = new Date(), nome = "", entendimento = null }) {
  const lista = [], hoje = isoData(agora);
  if (agora.getHours() < 12 && await umaVez(memoria, "bomdia:" + hoje)) lista.push(`Bom dia${nome ? ", " + nome : ""}! Hoje é ${dataPorExtenso(agora)}.`);
  for (const nota of await memoria.listar("Lembretes/")) {
    const para = /^Para: (\d{4}-\d{2}-\d{2})/m.exec(nota.corpo)?.[1];
    if (para && para <= hoje && await umaVez(memoria, "lembrete:" + nota.ref)) {
      lista.push(`🔔 Lembrete${para < hoje ? " (atrasado)" : ""}: ${nota.corpo.split("\n").slice(1).join(" ").trim() || nota.titulo}`);
    }
  }
  if (agora.getDay() === 1 && agora.getHours() >= 9) {
    const [ano, semana] = semanaIso(agora);
    const alvo = saber.topicos.filter((t) => t.area !== "logica")[semana % Math.max(1, saber.topicos.filter((t) => t.area !== "logica").length)];
    if (alvo && await umaVez(memoria, `treino:${ano}-${semana}`)) lista.push(`📚 Treino da semana — ${alvo.nome}: ${alvo.exercicios[0]}`);
  }
  const evolucao = await entendimento?.aprend.avisoSemanal().catch(() => null);  // "como estou evoluindo", uma vez por semana
  if (evolucao) lista.push(evolucao);
  const dia = Math.floor(agora / 86400000);
  const topico = saber.topicos[dia % Math.max(1, saber.topicos.length)];
  if (topico && await umaVez(memoria, "topico:" + hoje)) lista.push(`💡 Tópico do dia: **${topico.nome}** — ${topico.resumo.split(". ")[0]}. Pergunte "explique ${topico.nome}" para ver mais.`);
  return lista;
}
