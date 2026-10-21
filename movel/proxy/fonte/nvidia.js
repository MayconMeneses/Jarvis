// Rotas antigas, mantidas como eram: /v1/... -> NVIDIA e /brave/res/v1/... -> Brave Search. Só repassam os cabeçalhos de autenticação da lista.
const ROTAS = [
  { prefixo: "/v1/", destino: "https://integrate.api.nvidia.com", cabecalhos: ["authorization", "content-type"], tira: "" },
  { prefixo: "/brave/res/v1/", destino: "https://api.search.brave.com", cabecalhos: ["x-subscription-token", "accept"], tira: "/brave" },
];

export async function proxyApi(pedido, url, cors) {
  const rota = ROTAS.find((r) => url.pathname.startsWith(r.prefixo));
  if (!rota) return new Response("caminho não permitido", { status: 404, headers: cors });
  const cabecalhos = {};
  for (const nome of rota.cabecalhos) if (pedido.headers.get(nome)) cabecalhos[nome] = pedido.headers.get(nome);
  cabecalhos["content-type"] ||= "application/json";
  const resposta = await fetch(rota.destino + url.pathname.slice(rota.tira.length) + url.search, {
    method: pedido.method, headers: cabecalhos, body: pedido.method === "POST" ? await pedido.text() : undefined,
  });
  return new Response(resposta.body, { status: resposta.status, headers: { ...cors, "Content-Type": resposta.headers.get("Content-Type") || "application/json" } });
}
