// Proxy CORS para a NVIDIA e o Brave Search (Cloudflare Workers, plano grátis). Esses serviços não deixam o navegador chamar a API
// direto; este proxy recebe a chamada do app do celular e repassa. Ele NÃO guarda chave nenhuma: só repassa os cabeçalhos de
// autenticação, e só aceita pedidos vindos do endereço do app (ORIGEM). Como usar: veja docs/CELULAR-INDEPENDENTE.md.
//   /v1/...     -> https://integrate.api.nvidia.com/v1/...        (NVIDIA)
//   /brave/...  -> https://api.search.brave.com/...                (Brave Search)
const ORIGEM = "https://mayconmeneses.github.io";
const ROTAS = [
  { prefixo: "/v1/", destino: "https://integrate.api.nvidia.com", cabecalhos: ["authorization", "content-type"], tira: "" },
  { prefixo: "/brave/res/v1/", destino: "https://api.search.brave.com", cabecalhos: ["x-subscription-token", "accept"], tira: "/brave" },
];

export default {
  async fetch(pedido) {
    const cors = {
      "Access-Control-Allow-Origin": ORIGEM,
      "Access-Control-Allow-Headers": "authorization,content-type,x-subscription-token,accept",
      "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
      Vary: "Origin",
    };
    if (pedido.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (pedido.headers.get("Origin") !== ORIGEM) return new Response("origem não permitida", { status: 403 });
    const url = new URL(pedido.url);
    const rota = ROTAS.find((r) => url.pathname.startsWith(r.prefixo));
    if (!rota) return new Response("caminho não permitido", { status: 404, headers: cors });
    const cabecalhos = {};
    for (const nome of rota.cabecalhos) if (pedido.headers.get(nome)) cabecalhos[nome] = pedido.headers.get(nome);
    cabecalhos["content-type"] ||= "application/json";
    const resposta = await fetch(rota.destino + url.pathname.slice(rota.tira.length) + url.search, {
      method: pedido.method, headers: cabecalhos, body: pedido.method === "POST" ? await pedido.text() : undefined,
    });
    return new Response(resposta.body, { status: resposta.status, headers: { ...cors, "Content-Type": resposta.headers.get("Content-Type") || "application/json" } });
  },
};
