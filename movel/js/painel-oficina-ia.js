// Oficina > "Criar com IA": liga o fluxo de criar-ia.js ao cérebro escolhido pelo app (aparelho ou nuvem) e ao sandbox.
// A IA só escreve texto; os testes que ela roda aqui acontecem no ambiente isolado, e o programa em si só roda no botão Rodar.
import { criar } from "./criar-ia.js";
import { slug } from "./modelos.js";
import { executar } from "./sandbox.js";

const $ = (id) => document.getElementById(id);

export const SISTEMA = "Você é a Jarvis, programadora experiente. Escreva código simples e correto, com funções pequenas e nomes claros em português. "
  + "Prefira JavaScript (CommonJS: require e module.exports) ou Python. Nunca inclua senhas, chaves ou acesso à rede. Responda só no formato pedido.";

// conversa: async (mensagens) => texto. oficina: o painel da Oficina (espaço de arquivos + escolher o projeto).
export function ligarCriarComIA({ conversa, oficina, avisar }) {
  const dizer = (t) => { $("of-ia-status").textContent = t; };

  $("of-ia-criar").addEventListener("click", async () => {
    const descricao = $("of-ia-desc").value.trim();
    const nome = $("of-ia-nome").value.trim() || `IA ${slug(descricao).slice(0, 24)}`;
    if (!descricao) { dizer("Descreva o que criar."); return; }
    $("of-ia-criar").disabled = true;
    try {
      if ((await oficina.espaco.projetos()).includes(nome)) throw new Error("já existe um projeto com esse nome; escolha outro.");
      const r = await criar(nome, descricao, conversa, {
        sistema: SISTEMA,
        status: dizer,
        rodar: (linguagem, arquivos) => executar({ linguagem, arquivos, modo: "testar" }),
      });
      await oficina.espaco.criar(nome);
      for (const [caminho, texto] of Object.entries(r.arquivos)) await oficina.espaco.salvar(nome, caminho, texto);
      await oficina.escolher(nome);
      const aviso = r.avisos.length ? ` Avisos: ${r.avisos.join("; ")}.` : "";
      dizer(`Pronto: ${Object.keys(r.arquivos).length} arquivos em "${nome}". Leia o código, depois toque em Rodar ou Testar.${aviso}`);
      avisar(`Projeto "${nome}" criado com IA na Oficina.`);
    } catch (e) {
      dizer("Não consegui criar: " + e.message);
    } finally { $("of-ia-criar").disabled = false; }
  });
}
