// Aba Instagram: colar a tabela, importar, ver o relatório, comparar rodadas, ligar o lembrete semanal e apagar tudo (com confirmação).
const $ = (id) => document.getElementById(id);

export function ligarInstagram({ instagram, avisar }) {
  const mostrar = (texto) => { $("ig-saida").textContent = texto; };
  const rodar = (fn) => async () => { try { mostrar(await fn()); } catch (e) { avisar("Instagram: " + e.message); } };
  $("ig-importar").addEventListener("click", rodar(async () => {
    const texto = $("ig-dados").value;
    if (!texto.trim()) return "Cole a tabela de posts na caixa acima.";
    const r = await instagram.importar(texto);
    if (r.startsWith("Importei")) $("ig-dados").value = "";
    return r;
  }));
  $("ig-relatorio").addEventListener("click", rodar(() => instagram.relatorio()));
  $("ig-comparar").addEventListener("click", rodar(() => instagram.comparar()));
  $("ig-lembrete").addEventListener("change", () => instagram.definirLembrete($("ig-lembrete").checked));
  $("ig-apagar").addEventListener("click", rodar(async () => (window.confirm("Apagar TODOS os dados de Instagram deste aparelho?") ? instagram.apagar("tudo") : "Nada foi apagado.")));
  return async () => { $("ig-lembrete").checked = Boolean((await instagram.estado()).lembrete); };
}
