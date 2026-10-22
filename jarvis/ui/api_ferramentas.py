"""Painel ⚙ Cérebros: ferramentas externas do catálogo curado (listar, pedir instalação, desativar, remover). Tudo por cartão."""

from __future__ import annotations


class FerramentasMixin:
    def ferramentas_externas(self) -> list[dict]:
        """O catálogo curado com o estado de cada entrada (instalada, ativa) e o que o usuário precisa saber antes de aprovar."""
        from jarvis.mcp_catalogo import catalogo, instalados

        saida = []
        for item in catalogo.itens():
            reg = instalados.registro_de(item["id"])
            saida.append({"id": item["id"], "nome": item["nome"], "versao": item["versao"], "risco": item["risco"], "descricao": item["descricao"],
                          "permissoes": item["permissoes"], "riscos": item["riscos"], "fonte": item["fonte"],
                          "instalada": bool(reg), "ativa": bool(reg and reg.get("ativo") and reg.get("versao") == item["versao"])})
        return saida

    def ferramenta_externa_pedir(self, acao: str, id_: str) -> dict:
        """acao: instalar | desativar | remover. NÃO executa: devolve o cartão (em `acoes`) para o usuário aprovar na janela."""
        import time

        from jarvis.mcp_catalogo import cartoes

        acao, id_, inicio = str(acao), str(id_), time.time()
        if acao == "instalar":
            texto = cartoes.propor_instalar(id_, self._store)
        elif acao in ("desativar", "remover"):
            texto = cartoes.propor_remover(id_, self._store, desativar=acao == "desativar")
        else:
            return {"ok": False, "mensagem": "ação inválida"}
        cartoes_novos = [{"id": a.id, "descricao": a.descricao, "motivo": a.motivo} for a in self._store.pending_since(inicio)]
        return {"ok": bool(cartoes_novos), "mensagem": texto, "acoes": cartoes_novos}
