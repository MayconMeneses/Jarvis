"""Ponte da janela com a Oficina (IDE): projetos e arquivos, rodar, testar, desfazer e criar com IA."""

from __future__ import annotations

import logging
import threading

from jarvis.oficina import ia, sandbox
from jarvis.oficina.espaco import Espaco

log = logging.getLogger(__name__)


class OficinaMixin:
    """Tudo aqui trabalha só dentro da pasta da Oficina; rodar e testar são cliques do usuário, no sandbox."""

    _espaco: Espaco | None = None
    _of_job: dict | None = None

    def _of(self) -> Espaco:
        if self._espaco is None:
            self._espaco = Espaco()
        return self._espaco

    def of_projetos(self) -> dict:
        return {"projetos": self._of().projetos(), "python": sandbox.interpretador("python") is not None,
                "node": sandbox.interpretador("javascript") is not None}

    def of_criar_projeto(self, nome: str) -> dict:
        try:
            self._of().criar(str(nome).strip())
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}
        return self.of_projetos()

    def of_abrir(self, projeto: str) -> dict:
        try:
            return {"arquivos": self._of().arquivos(str(projeto))}
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}

    def of_salvar(self, projeto: str, caminho: str, conteudo: str) -> dict:
        try:
            nome = self._of().salvar(str(projeto), str(caminho), str(conteudo))
            return {"ok": True, "caminho": nome, "versoes": self._of().versoes(str(projeto), nome)}
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}

    def of_apagar(self, projeto: str, caminho: str) -> dict:
        try:
            return {"ok": self._of().apagar(str(projeto), str(caminho))}
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}

    def of_desfazer(self, projeto: str, caminho: str) -> dict:
        try:
            return {"ok": True, "conteudo": self._of().desfazer(str(projeto), str(caminho))}
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}

    def _linguagem(self, caminho: str) -> str:
        return "javascript" if str(caminho).endswith(".js") else "python"

    def of_rodar(self, projeto: str, caminho: str) -> dict:
        """Roda o arquivo (já salvo) num sandbox: processo separado, pasta temporária, 10 s e 512 MB."""
        try:
            arquivos = self._of().arquivos(str(projeto))
            if str(caminho) not in arquivos:
                return {"error": "salve o arquivo antes de rodar"}
            r = sandbox.rodar(self._linguagem(caminho), arquivos, str(caminho))
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}
        self._diary(f"Oficina: rodou {caminho} ({'ok' if r.ok else 'falhou'})")
        return {"texto": r.texto(), "ok": r.ok}

    def of_testar(self, projeto: str, linguagem: str = "python") -> dict:
        try:
            r = sandbox.testar("javascript" if linguagem == "javascript" else "python", self._of().arquivos(str(projeto)))
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}
        self._diary(f"Oficina: testes do projeto {projeto} ({'ok' if r.ok else 'falharam'})")
        return {"texto": r.texto(), "ok": r.ok}

    # ── criar com IA (demora: roda numa thread e a janela consulta o andamento) ──
    def of_criar_ia(self, projeto: str, descricao: str) -> dict:
        if self._of_job and self._of_job.get("rodando"):
            return {"error": "já estou criando um projeto; espere terminar"}
        try:
            self._of().criar(str(projeto).strip())
        except (ValueError, OSError) as exc:
            return {"error": str(exc)}
        job = self._of_job = {"rodando": True, "status": "começando…", "projeto": str(projeto).strip()}

        def trabalho() -> None:
            try:
                conversa = ia.conversa_do_roteador(self._conversation.router, "Você escreve código simples, correto e com testes.")
                feito = ia.criar(str(descricao), conversa, self._cfg, lambda t: job.update(status=t), job["projeto"])
                for caminho, conteudo in feito["arquivos"].items():
                    self._of().salvar(job["projeto"], caminho, conteudo)
                job.update(resultado={"principal": feito["principal"], "linguagem": feito["linguagem"], "testes": feito["testes"], "avisos": feito["avisos"],
                                      "arquivos": sorted(feito["arquivos"])})
                self._diary(f"Oficina: criou o projeto {job['projeto']} com IA")
            except Exception as exc:  # noqa: BLE001  (o motivo aparece na janela)
                log.info("criar com IA falhou: %s", exc)
                job.update(erro=str(exc))
            finally:
                job["rodando"] = False

        threading.Thread(target=trabalho, daemon=True, name="jarvis-oficina-ia").start()
        return {"ok": True}

    def of_estado_ia(self) -> dict:
        return dict(self._of_job or {"rodando": False})
