// Entrega o arquivo criado: folha de compartilhamento do iOS (navigator.share com File, que deixa "Salvar em Arquivos") ou download comum.
// Precisa ser chamado por um toque do usuário (regra do Safari para compartilhar).
export async function entregar({ nome, bytes, mime }, { nav = globalThis.navigator, doc = globalThis.document, urls = globalThis.URL } = {}) {
  const arquivo = new File([bytes], nome, { type: mime });
  if (nav?.canShare?.({ files: [arquivo] })) {
    try { await nav.share({ files: [arquivo], title: nome }); return "compartilhado"; } catch (e) {
      if (e?.name === "AbortError") return "cancelado";  // o usuário fechou a folha: não é erro
    }
  }
  const url = urls.createObjectURL(arquivo);
  const a = Object.assign(doc.createElement("a"), { href: url, download: nome });
  doc.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => urls.revokeObjectURL(url), 60000);
  return "baixado";
}
