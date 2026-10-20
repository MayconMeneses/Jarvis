"""Entrevista curta: o perfil da análise (nicho, @ próprio, concorrentes, objetivo, pesos...).

Sem estado escondido: cada resposta ("campo: valor", uma por linha ou separadas por ";") é gravada, e o que ainda falta
é recalculado a cada vez. O usuário responde tudo de uma vez ou aos poucos.
"""

from __future__ import annotations

import re

from jarvis.instagram import PESOS_PADRAO, fold
from jarvis.instagram.importar import normalizar_perfil, numero

CAMPOS = (
    ("nicho", "nicho", "nicho (ex.: nutrição esportiva)"),
    ("proprio", "meu perfil", "o seu @ (ex.: meu perfil: @voce)"),
    ("concorrentes", "concorrentes", "5 a 15 concorrentes com seguidores (ex.: concorrentes: @a (12,3 mil), @b (8 mil))"),
    ("objetivo", "objetivo", "objetivo (ex.: objetivo: vender mentoria)"),
    ("vitoria", "vitória", "como mede vitória (ex.: vitória: 500 novos seguidores por mês)"),
    ("pesos", "pesos", "pesos do engajamento (ex.: pesos: salvamentos 3, compartilhamentos 3, comentários 2, likes 1; vazio = esses)"),
    ("formatos", "formatos", "formatos que posta (ex.: formatos: reels, carrossel)"),
    ("frequencia", "frequência", "frequência (ex.: frequência: 4 por semana)"),
    ("temas_suspeitos", "temas suspeitos", "temas que acha que funcionam (ex.: temas suspeitos: receitas, treino)"),
    ("origem", "dados", "de onde vêm os dados (dados: importação ou pesquisa pública)"),
)
OPCIONAIS = {"pesos", "temas_suspeitos", "frequencia", "origem"}
_ALIAS = {"nicho": "nicho", "meu perfil": "proprio", "perfil": "proprio", "arroba": "proprio", "meu arroba": "proprio", "proprio": "proprio",
          "concorrentes": "concorrentes", "objetivo": "objetivo", "vitoria": "vitoria", "definicao de vitoria": "vitoria", "pesos": "pesos",
          "formatos": "formatos", "frequencia": "frequencia", "temas suspeitos": "temas_suspeitos", "temas": "temas_suspeitos",
          "dados": "origem", "origem dos dados": "origem", "fonte": "origem"}
_CAMPO = re.compile(r"(?:^|[\n;])\s*([a-zA-ZÀ-ÿ ]{3,25}?)\s*:\s*", re.M)


def separar_respostas(texto: str) -> dict[str, str]:
    """"nicho: x; objetivo: y" -> {"nicho": "x", "objetivo": "y"}. Chaves desconhecidas são ignoradas."""
    achados = list(_CAMPO.finditer(texto))
    respostas = {}
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        campo = _ALIAS.get(fold(m.group(1)).strip())
        if campo:
            respostas[campo] = texto[m.end():fim].strip(" ;\n")[:600]
    return respostas


def parse_pesos(texto: str) -> dict:
    """"salvamentos 3, comentários 2" -> pesos; o que não for citado fica no padrão. Valor inválido gera ValueError."""
    pesos = dict(PESOS_PADRAO)
    for nome, valor in re.findall(r"(salvamentos?|compartilhamentos?|coment\w+|likes?|curtidas?)\s*(?:=|:|x)?\s*(\d+(?:[.,]\d+)?)", fold(texto)):
        campo = ("salvamentos" if nome.startswith("salv") else "compartilhamentos" if nome.startswith("compart")
                 else "comentarios" if nome.startswith("coment") else "likes")
        pesos[campo] = float(valor.replace(",", "."))
        pesos[campo] = int(pesos[campo]) if pesos[campo].is_integer() else pesos[campo]
    if texto.strip() and pesos == PESOS_PADRAO and not re.search(r"padrao|\d", fold(texto)):
        raise ValueError("não entendi os pesos (use: salvamentos 3, compartilhamentos 3, comentários 2, likes 1)")
    return pesos


def parse_concorrentes(texto: str) -> dict[str, int | None]:
    """"@a (12,3 mil), @b (8 mil), @c" -> {"@a": 12300, "@b": 8000, "@c": None}."""
    saida = {}
    for parte in re.split(r",(?![^()]*\))|;", texto):
        m = re.match(r"\s*(@?[\w.]{1,30})\s*(?:\(([^)]*)\))?", parte)
        arroba = normalizar_perfil(m.group(1)) if m else ""
        if m and arroba and re.search(r"[a-z]", arroba):
            saida[arroba] = numero(re.sub(r"\s*seguidores?", "", m.group(2) or "", flags=re.I))
    return saida


def aplicar(texto: str, atual: dict | None = None) -> tuple[dict, list[str], list[str]]:
    """Mistura as respostas novas no perfil. Devolve (perfil, perguntas que faltam, avisos)."""
    perfil, avisos = dict(atual or {}), []
    for campo, valor in separar_respostas(texto).items():
        try:
            if campo == "pesos":
                perfil["pesos"] = parse_pesos(valor)
            elif campo == "proprio":
                perfil["proprio"] = normalizar_perfil(valor.split()[0] if valor.split() else "")
            elif campo == "concorrentes":
                perfil["concorrentes"] = parse_concorrentes(valor)
                if not 5 <= len(perfil["concorrentes"]) <= 15:
                    avisos.append(f"Você citou {len(perfil['concorrentes'])} concorrentes; o ideal são 5 a 15 (segue assim mesmo).")
            else:
                perfil[campo] = valor
        except ValueError as exc:
            avisos.append(str(exc))
    faltam = [pergunta for campo, _, pergunta in CAMPOS if campo not in OPCIONAIS and not perfil.get(campo)]
    return perfil, faltam, avisos
