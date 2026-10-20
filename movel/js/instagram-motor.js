// Comandos de conversa do analista de Instagram no celular. O objeto `instagram` é ligado pelo main.js (como o `autonomo`); sem ele, o motor avisa.
const EXTRAS = [
  ["ig_pesquisar", /^pesquis\w+\s+(o\s+)?(perfil\s+)?(d[eo]\s+)?instagram\s+(d[eo]\s+)?@?\w[\w.]*$/],
  ["ig_importar", /^importar posts\b[\s\S]*$/],
  ["ig_configurar", /^configurar (a )?(analise d[eo] )?instagram\b[\s\S]*$/],
  ["ig_relatorio", /^relatorio (de|do|sobre o) instagram$/],
  ["ig_comparar", /^compar\w+ com a rodada anterior$|^compar\w+ (as )?rodadas$/],
  ["ig_apagar", /^(confirmo )?(apag\w+|exclu\w+|delet\w+)\s+(os\s+)?(dados|posts|serie)\s+(d[eo]\s+)?instagram\b.*$/],
  ["ig_lembrete", /^(lembrete semanal d[eo] instagram\b.*\b(lig\w+|ativ\w+|deslig\w+|desativ\w+)|(lig\w+|ativ\w+|deslig\w+|desativ\w+) (o )?lembrete semanal d[eo] instagram)$/],
  ["ig_analisar", /^(analis\w+|come\w+ (a )?analise (de |do )?)\s*(o\s+|meu\s+)?instagram$/],
];
const SEM = "O analista de Instagram ainda não está carregado.";

const HANDLERS = {
  async _ig_configurar(texto) { return this.instagram ? this.instagram.configurar(texto.replace(/^\s*configurar\s+(a\s+)?(an[aá]lise\s+d[eo]\s+)?instagram[:\s]*/i, "")) : SEM; },
  async _ig_importar(texto) {
    if (!this.instagram) return SEM;
    const [primeira, ...resto] = texto.trim().split("\n"), cabeca = primeira.replace(/^\s*importar posts\s*/i, "").trim();
    const nova = /\bnova rodada\b/i.test(cabeca), perfil = /^(?:de|do)\s+(@?[\w.]+)\s*(?:nova rodada)?$/i.exec(cabeca.replace(/\bnova rodada\b/i, "").trim());
    if (!resto.join("\n").trim()) return "Cole a tabela na linha seguinte (primeira linha com os nomes das colunas: perfil, link, data, formato, legenda, likes, comentarios, views).";
    try { return await this.instagram.importar(resto.join("\n"), perfil ? perfil[1] : "", nova); } catch (e) { return `Não consegui importar: ${e.message}`; }
  },
  async _ig_relatorio() { return this.instagram ? this.instagram.relatorio() : SEM; },
  async _ig_comparar() { return this.instagram ? this.instagram.comparar() : SEM; },
  async _ig_analisar() { return this.instagram ? this.instagram.analisarComando() : SEM; },
  async _ig_pesquisar() {
    return "No celular eu não pesquiso perfis do Instagram (o site exige login e não permite coleta automática). Informe os seguidores em \"configurar instagram concorrentes: @fulano (12,3 mil)\" ou cole os dados.";
  },
  async _ig_apagar(texto, limpo) {
    if (!this.instagram) return SEM;
    const alvo = /(@[\w.]+)/.exec(texto)?.[1]?.toLowerCase() || "tudo", confirmou = limpo.startsWith("confirmo");
    if (!confirmou) return `Isto apaga os dados de ${alvo === "tudo" ? "TODO o Instagram" : alvo} deste aparelho. Para confirmar, diga: "confirmo apagar dados do instagram${alvo === "tudo" ? "" : " de " + alvo}".`;
    return this.instagram.apagar(alvo);
  },
  async _ig_lembrete(texto, limpo) {
    if (!this.instagram) return SEM;
    const ligar = !/deslig|desativ/.test(limpo);
    await this.instagram.definirLembrete(ligar);
    return ligar ? "Lembrete semanal do Instagram ligado: ao abrir o app numa segunda-feira (9h às 20h) eu aviso e falo em voz alta." : "Lembrete semanal do Instagram desligado.";
  },
};

export function instalarInstagram(Motor, padroes) {
  padroes.unshift(...EXTRAS);
  Object.assign(Motor.prototype, HANDLERS);
}
