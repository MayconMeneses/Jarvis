// Motor próprio de regras (funciona sem IA e sem internet): entende pedidos pelo padrão da frase e responde com o que sabe.
import { aprender, consultarAprendido, pesquisar } from "./aprender.js";
import * as design from "./design.js";
import * as gerar from "./gerar.js";
import { Habilidades } from "./habilidades.js";
import { instalarAutonomo } from "./motor-autonomo.js";
import { instalarExtras } from "./motor-extra.js";
import { instalarInstagram } from "./instagram-motor.js";
import { Stack } from "./stack.js";
import { dataPorExtenso, dois, fold, isoData } from "./util.js";

export const limpar = (texto) => fold(texto).trim().replace(/^(ei|ok|hey|oi|ola)?[\s,]*jarvis[\s,:!.]*/, "").replace(/[?!.]+$/, "").trim()
  .replace(/^((por favor|pfv)[\s,]+|((voce|vc)\s+)?(pode|poderia|consegue)\s+(me\s+)?)+/, "").replace(/[\s,]+(por favor|pfv)$/, "");

const COR = "(#[0-9a-f]{3}(?:[0-9a-f]{3})?|\\b[0-9a-f]{6}\\b)";
export const PADROES = [
  ["hora", /\b(que horas?|hora atual|horas sao)\b/],
  ["data", /\b(que dia e hoje|data de hoje|qual (a|e a) data|que dia e)\b/],
  ["lembrete", /^(me\s+)?(lembr\w+|avis\w+)\s+(de\s+|que\s+)?.+\s+(hoje|amanha|depois de amanha|dia \d{1,2}|em \d+ dias?)$/],
  ["esquecer", /^(esquec\w+|apag\w+)\s+(a\s+)?(nota|memoria)\s+.+$/],
  ["memoria", /^(o que voce (sabe|lembra)( sobre| de| do| da)?\b.*|(busqu\w*|procur\w*|pesquis\w*)\s+(na|nas|em)\s+(minha\s+)?(memoria|notas)\b.*|minhas notas|minha memoria)$/],
  ["lembrar", /^(lembr\w*|anot\w*|guard\w*|memoriz\w*)\s+(de\s+)?(que\s+)?.{3,}$/],
  ["aprender", /^(aprend\w+|estud\w+)\s+(sobre|a respeito de)\s+.{3,}$/],
  ["ux", new RegExp(`^(?=.*${COR}).*\\b(contraste|paleta|tokens?)\\b|\\b(escala tipografica|escala de tipos)\\b`)],
  ["gerar", /^(cri[ae]|ger[ae]|gerar|faca|escrev\w+|mont[ae])\s+(um|uma|o|a)?\s*(tabela|esquema sql|adr|registro de decisao|historia de usuario|openapi|swagger|workflow|pipeline|dockerfile|editorconfig)\b.*$/],
  ["comparar", /^(compar\w+|diferenca entr[ae]|qual (e )?a diferenca entr[ae])\b.+|\b(vs|versus)\b/],
  ["padrao", /\b(padroes? de projeto|design patterns?|padrao (strategy|observer|factory|decorator|adapter|repository|command|builder))\b/],
  ["algoritmo", /^(como (fazer|faco|escrever|implementar|programar|criar|calcular)|escreva|escrever|mostre|mostra|me mostre|me de|exemplo de|algoritmo (de|para)|codigo (de|para)|implemente|programa (de|para))\b.+$/],
  ["explicar", /^(o que (e|sao)|que (e|sao)|fale sobre|me fale sobre|explique|explica|me explica|descreva|conte sobre)\s+.+$/],
  ["pesquisa", /^(pesquis\w*|procur\w*|busc\w*|busqu\w*)\s+(informac\w+\s+)?(sobre\s+|de\s+)?.{3,}$/],
  ["ajuda", /^(ajuda|o que voce (faz|sabe fazer)|comandos|me ajuda)$/],
];
// O que o modelo de IA pode receber já pronto, como dado real (só leitura).
export const CONSULTAS_PARA_IA = new Set(["hora", "data", "memoria", "ux", "comparar"]);

export const AJUDA = "Estou no **modo independente** (rodo só neste celular, sem servidor). Consigo:\n"
  + "- **clima, notícias, vagas** (\"clima em Fortaleza\", \"notícias de tecnologia\", \"vagas\" depois de \"minha stack é Python e React\"), **projetos** (\"anota no projeto Loja que ...\", \"ficha do projeto Loja\")\n"
  + "- **evoluir**: \"quais habilidades de programador\", \"treino da semana\", \"checklist de segurança\", \"revise este diff\" (cole o diff na linha seguinte), \"qual stack para uma loja virtual\"\n"
  + "- **hora e data**, **memória** (\"lembre que...\", \"me lembre de ligar para o João amanhã\", \"o que você sabe sobre mim\", \"apague a nota X\")\n"
  + "- **programação**: \"explique SOLID\", \"mostre o padrão Observer em JavaScript\", \"como fazer fatorial em Go\", \"compare React e Vue\"\n"
  + "- **design**: \"contraste #767676 sobre #ffffff\", \"paleta a partir de #3b82f6\", \"tokens css para #3b82f6\", \"escala tipográfica\"\n"
  + "- **gerar**: \"crie uma tabela clientes com nome texto, idade inteiro\", \"gere um dockerfile para node\", \"gere um workflow para python\"\n"
  + "- **internet**: \"pesquise sobre ...\" e \"aprenda sobre ...\" (Wikipédia; guardo o resumo na memória)\n"
  + "- **cérebro de IA no celular** (aba Cérebro): conversa livre e ideias, sem enviar nada para fora.";

const para = (limpo, regex) => regex.exec(limpo);

export class Motor {
  constructor({ saber, memoria, buscar, agora = () => new Date(), brave = null }) {
    Object.assign(this, { saber, memoria, buscar, agora, brave });
    this.stack = new Stack(saber.tecnologias, saber.tipos);
    this.habil = new Habilidades(saber.habilidades, saber);
  }

  classificar(texto) {
    const baixo = limpar(texto);
    const achado = PADROES.find(([, regex]) => regex.test(baixo));
    return achado ? achado[0] : null;
  }

  async responder(texto) {
    const intencao = this.classificar(texto);
    if (!intencao) return null;
    try { return await this[`_${intencao}`](texto, limpar(texto)); } catch (e) { return `Tentei, mas não consegui: ${e.message}`; }
  }

  // Dado real para o modelo de IA redigir em cima (não depende de ele lembrar de pedir).
  async consultarAntes(texto) {
    const intencao = this.classificar(texto);
    return intencao && CONSULTAS_PARA_IA.has(intencao) ? this.responder(texto) : null;
  }

  async fallback(texto) {
    const explicado = this.saber.explicar(texto, this.saber.linguagem(texto)) || await this._aprendido(texto);
    return explicado || AJUDA;
  }

  async _aprendido(texto) {
    const sabido = await consultarAprendido(texto, this.memoria);
    return sabido ? `Do que aprendi na internet (não verificado):\n\n${sabido}` : null;
  }

  _hora() { const a = this.agora(); return `Agora são ${dois(a.getHours())}:${dois(a.getMinutes())}.`; }
  _data() { return `Hoje é ${dataPorExtenso(this.agora())}.`; }
  _ajuda() { return AJUDA; }

  async _lembrar(texto) {
    const fato = texto.replace(/^\s*(lembr\w*|anot\w*|guard\w*|memoriz\w*)\s+(de\s+)?(que\s+)?/i, "").trim();
    await this.memoria.guardar(`Lembranças/${fato.slice(0, 50)}`, fato, "lembranca");
    await this.memoria.diario(`Lembrei: ${fato.slice(0, 120)}`);
    return `Guardei: "${fato}". Você vê e edita na aba Memória.`;
  }

  async _lembrete(texto, limpo) {
    const achado = para(limpo, /^(?:me\s+)?(?:lembr\w+|avis\w+)\s+(?:de\s+|que\s+)?(.+?)\s+(hoje|amanha|depois de amanha|dia (\d{1,2})|em (\d+) dias?)$/);
    const quando = this.agora();
    if (achado[2] === "amanha") quando.setDate(quando.getDate() + 1);
    else if (achado[2] === "depois de amanha") quando.setDate(quando.getDate() + 2);
    else if (achado[4]) { quando.setDate(+achado[4]); if (quando < this.agora()) quando.setMonth(quando.getMonth() + 1); }
    else if (achado[5]) quando.setDate(quando.getDate() + +achado[5]);
    const original = texto.replace(/^\s*(me\s+)?(lembr\w+|avis\w+)\s+(de\s+|que\s+)?/i, "").replace(/\s+(hoje|amanh[ãa]|depois de amanh[ãa]|dia \d{1,2}|em \d+ dias?)\s*[.!?]*$/i, "").trim();
    await this.memoria.guardar(`Lembretes/${isoData(quando)} ${original.slice(0, 40)}`, `Para: ${isoData(quando)}\n${original}`, "lembrete");
    return `Combinado! Eu lembro você de "${original}" em ${dataPorExtenso(quando)} (aparece quando você abrir a Jarvis nesse dia).`;
  }

  async _esquecer(texto, limpo) {
    const nome = texto.replace(/^\s*(esquec\w+|apag\w+)\s+(a\s+)?(nota|mem[óo]ria)\s+/i, "").trim();
    const nota = (await this.memoria.listar()).find((n) => fold(n.ref).includes(fold(nome)));
    if (!nota) return `Não achei uma nota com "${nome}".`;
    await this.memoria.apagar(nota.ref);
    return `Apaguei a nota "${nota.ref}".`;
  }

  async _memoria(texto, limpo) {
    const tema = limpo.replace(/^(o que voce (sabe|lembra)( sobre| de| do| da)?|(busqu\w*|procur\w*|pesquis\w*)\s+(na|nas|em)\s+(minha\s+)?(memoria|notas)( sobre| de)?|minhas notas|minha memoria)\s*/, "").trim();
    const util = (n) => !n.ref.startsWith("Diário/");  // o diário registra os pedidos: não vale como "o que sei"
    const notas = tema ? (await this.memoria.buscar(tema, 12)).filter(util).slice(0, 5) : (await this.memoria.listar()).filter(util).slice(0, 8);
    if (!notas.length) return tema ? `Não achei nada sobre "${tema}" na minha memória.` : "Minha memória ainda está vazia. Diga \"lembre que ...\" para eu guardar algo.";
    return "**Na minha memória:**\n" + notas.map((n) => `- **${n.titulo}**: ${n.corpo.replace(/\n/g, " ").slice(0, 140)}`).join("\n");
  }

  _aprender(texto) { return aprender(texto, this.memoria, this.buscar, this.brave); }
  _pesquisa(texto) { return pesquisar(texto, this.buscar, this.brave); }

  _ux(texto) {
    const baixo = texto.toLowerCase();
    try {
      if (baixo.includes("contraste")) {
        const duas = [...texto.matchAll(/#?\b([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b/g)].map((m) => "#" + m[1]);
        return duas.length >= 2 ? design.avaliarContraste(duas[0], duas[1]) : 'Diga as duas cores, por exemplo: "contraste #767676 sobre #ffffff".';
      }
      const uma = /(#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?|\b[0-9a-fA-F]{6}\b)/.exec(texto);
      const cor = uma ? (uma[1].startsWith("#") ? uma[1] : "#" + uma[1]) : null;
      if (baixo.includes("token") && cor) return "```css\n" + design.tokensCss(cor) + "\n```";
      if (baixo.includes("paleta")) return cor ? design.relatorioPaleta(cor) : 'Diga a cor base, por exemplo: "paleta a partir de #3b82f6".';
      return design.relatorioEscala();
    } catch (e) { return `Não consegui: ${e.message}`; }
  }

  _campos(trecho) {
    const campos = {};
    for (const parte of trecho.trim().split(/\s*(?:,|\be\b)\s*/)) {
      const [nome, tipo] = parte.split(/\s+/);
      if (nome) campos[nome] = /^(texto|inteiro|numero|decimal|data|booleano|bool)$/i.test(tipo || "") ? tipo : "texto";
    }
    return campos;
  }

  _gerar(texto) {
    const baixo = texto.toLowerCase();
    try {
      if (/\b(tabela|esquema sql)\b/.test(baixo)) {
        const m = /(?:tabela|esquema sql)\s+(?:de\s+|do\s+|da\s+)?(\w+)(?:\s+com\s+(.+))?/i.exec(texto);
        return m ? "```sql\n" + gerar.esquemaSql(m[1], this._campos(m[2] || "")) + "\n```" : 'Diga a tabela e os campos, por exemplo: "crie uma tabela clientes com nome texto, idade inteiro".';
      }
      if (/\b(adr|decis[ãa]o de arquitetura|registro de decis[ãa]o)\b/.test(baixo)) {
        const titulo = texto.replace(/^.*?\b(adr|decis[ãa]o de arquitetura|registro de decis[ãa]o)\b\s*(?:sobre|para|de|:)?\s*/i, "").trim() || "Título da decisão";
        return "```markdown\n" + gerar.adr(titulo, "Descreva o problema e as restrições.", "Descreva o que foi decidido.", "", 1, this.agora()) + "\n```";
      }
      if (/\bhist[óo]ria de usu[áa]rio\b/.test(baixo)) return gerar.historiaUsuario("usuário", "realizar a ação desejada", "alcançar o objetivo");
      if (/\b(openapi|swagger)\b/.test(baixo)) {
        const recursos = [...baixo.split(/openapi|swagger/).pop().matchAll(/\b(?:de|para|com)\s+(\w+)/g)].map((m) => m[1]);
        return "```yaml\n" + gerar.openapi("API", recursos.length ? recursos : ["itens"]) + "```";
      }
      const lang = this.saber.linguagem(texto, "python");
      if (/\b(workflow|pipeline|ci)\b/.test(baixo)) return "```yaml\n" + gerar.workflowCi(lang) + "```";
      if (baixo.includes("dockerfile")) return "```dockerfile\n" + gerar.dockerfile(lang) + "```";
      if (baixo.includes("editorconfig")) return "```ini\n" + gerar.editorconfig() + "```";
    } catch (e) { return `Não consegui gerar: ${e.message}`; }
    return "Posso gerar: tabela SQL, ADR, história de usuário, OpenAPI, workflow de CI, Dockerfile e .editorconfig.";
  }

  _comparar(texto) {
    const tecnologias = this.saber.constructor.citados(this.saber.tecnologias, texto);
    if (tecnologias.length >= 2) return this.stack.comparar(tecnologias[0], tecnologias[1]);  // "React e Vue", "Django ou FastAPI"
    const itens = [...this.saber.citadosTopicos(texto), ...tecnologias];
    return itens.length >= 2 ? this.saber.comparar(itens[0], itens[1]) : 'Diga os dois itens, por exemplo: "compare React e Vue" ou "diferença entre pilha e fila".';
  }

  _padrao(texto) {
    const achado = this.saber.padrao(texto);
    if (achado) return this.saber.mostrar(achado, this.saber.linguagem(texto));
    const geral = this.saber.topico("padroes de projeto");
    return (geral ? this.saber.descrever(geral) + "\n\n" : "") + "**Padrões que eu sei escrever:** " + this.saber.padroes.map((p) => p.nome).join(", ") + '.\nPeça: "mostre o padrão Observer em JavaScript".';
  }

  async _algoritmo(texto) {
    const achado = this.saber.algoritmo(texto);
    if (achado) return this.saber.mostrar(achado, this.saber.linguagem(texto));
    return this.fallback(texto);
  }

  async _explicar(texto, limpo) {
    const tema = limpo.replace(/^(o que (e|sao)|que (e|sao)|fale sobre|me fale sobre|explique|explica|me explica|descreva|conte sobre)\s+/, "");
    const tecnologia = this.saber.tecnologia(tema);
    const achado = (tecnologia && this.stack.descrever(tecnologia)) || this.saber.explicar(tema, this.saber.linguagem(texto)) || await this._aprendido(tema);
    return achado || pesquisar(tema, this.buscar, this.brave);
  }
}

instalarExtras(Motor, PADROES);
instalarAutonomo(Motor, PADROES);
instalarInstagram(Motor, PADROES);
