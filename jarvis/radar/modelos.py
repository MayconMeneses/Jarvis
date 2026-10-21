"""Dados que circulam pelo Radar. Só dataclasses simples, sem lógica de rede ou de disco."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Fonte:
    nome: str
    feed: str
    tipo: str = "imprensa"  # imprensa | oficial | especialista | comunidade | contraponto | cientifico
    idioma: str = "pt"
    nota: float = 5.0  # 0 a 10
    medida: bool = False  # False = credibilidade/originalidade são palpite (padrão 5), não medição
    ativa: bool = True


@dataclass
class Artigo:
    fonte: str
    titulo: str
    link: str
    quando: float = 0.0  # epoch em segundos; 0 = o feed não informou a data
    resumo: str = ""  # trecho do feed, limpo e curto (nunca o corpo do artigo)
    autor: str = ""
    categorias: tuple[str, ...] = ()
    nota_fonte: float = 5.0
    tipo_fonte: str = "imprensa"


@dataclass
class Item:
    """Um artigo escolhido para o boletim, já pontuado e (talvez) resumido."""

    artigo: Artigo
    nota: int = 0
    motivos: list[str] = field(default_factory=list)
    tambem_em: list[str] = field(default_factory=list)
    papel: str = "principal"  # principal | radar
    manchete: str = ""
    linhas: list[str] = field(default_factory=list)  # o que aconteceu (frases do lead, sem IA)
    por_que: str = ""
    rotulo: str = "não classificado"  # fato | opinião | paywall | não confirmado | não classificado
    origem: str = "rss"  # rss = só o trecho do feed; artigo = a página foi lida
    palavras: int = 0  # tamanho do artigo lido (para "leitura X min"); 0 = não lido
    suspeito: str = ""  # motivo, quando o texto tenta dar ordens à IA (o item não vai à IA)
    jargao: str = ""  # só com IA: termo técnico explicado em uma frase
    angulo: str = ""  # só com IA: como isso vira post, argumento ou decisão
    texto_fonte: str = ""  # texto lido (não é gravado em disco): base para conferir o que a IA escreve


@dataclass
class Boletim:
    dia: str
    nicho: str
    itens: list[Item] = field(default_factory=list)
    conexoes: list[str] = field(default_factory=list)
    observar: list[str] = field(default_factory=list)
    varridos: int = 0
    falhas: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    com_ia: bool = False
    atrasado: bool = False
