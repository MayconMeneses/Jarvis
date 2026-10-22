// Os dois caminhos de IA da conversa: o cérebro do APARELHO (WebLLM) e a NUVEM (as chaves do usuário). Cada um mostra a resposta numa bolha e devolve o texto.
// Em qualquer falha (erro, prazo estourado) a bolha some e o erro sobe: quem decide o que fazer depois é o pensador (pensar.js), que nunca deixa em silêncio.
import { limite } from "./limite.js";
import { extrair, semProposta } from "./memoria-viva.js";

// d: { saber, memoria, motor, cerebro, nuvem, conversa, contexto, nome(), cartoes(propostas, dados), agentes, adicionar, atualizar, pensando }
export function criarCaminhos(d) {
  const sistema = async (texto) => {
    const dados = (await d.motor.consultarAntes(texto)) || "";
    return { dados, sistema: await d.contexto.sistema({ saber: d.saber, memoria: d.memoria, pergunta: texto, nome: await d.nome(), dados, app: d.motor.entendimento?.contextoApp(texto) || "" }) };
  };

  async function perguntarAparelho(texto, limiteMs) {
    const { dados, sistema: prompt } = await sistema(texto);
    const mensagens = [{ role: "system", content: prompt }, ...d.conversa.paraPrompt()];  // cabe no contexto do modelo, sempre
    const bolha = d.adicionar("…", "jarvis", d.cerebro.modelo);
    d.pensando(true, "IA pensando…");
    try {
      const resposta = await limite(d.cerebro.perguntar(mensagens, (parcial) => d.atualizar(bolha, semProposta(parcial)), (aviso) => d.atualizar(bolha, aviso)), limiteMs);
      d.agentes.marcar("cerebro", "ok");
      const { texto: limpo, propostas } = extrair(resposta || "");
      if (!limpo) throw new Error("o cérebro do aparelho devolveu uma resposta vazia");
      d.atualizar(bolha, limpo);
      await d.cartoes(propostas, dados);
      return limpo;
    } catch (e) {
      d.agentes.marcar("cerebro", "erro");
      bolha.remove();
      throw e;
    } finally { d.pensando(false); }
  }

  // Nuvem: histórico maior, porque esses modelos aguentam bem mais contexto.
  async function perguntarNuvem(texto, limiteMs) {
    const { dados, sistema: prompt } = await sistema(texto);
    const bolha = d.adicionar("…", "jarvis");
    d.pensando(true, "consultando a nuvem…");
    try {
      const r = await limite(d.nuvem.perguntar([{ role: "system", content: prompt }, ...d.conversa.paraPrompt(9000)], (parcial) => d.atualizar(bolha, semProposta(parcial))), limiteMs);
      const { texto: limpo, propostas } = extrair(r.texto);
      if (!limpo) throw new Error("a nuvem devolveu uma resposta vazia");
      d.atualizar(bolha, limpo);
      const nota = document.createElement("small");
      nota.textContent = r.provedor;
      bolha.appendChild(nota);
      await d.cartoes(propostas, dados);
      return limpo;
    } catch (e) {
      bolha.remove();
      throw e;
    } finally { d.pensando(false); }
  }
  return { perguntarAparelho, perguntarNuvem };
}
