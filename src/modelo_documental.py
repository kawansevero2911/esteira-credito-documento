"""Modelo documental: representacao intermediaria entre o contrato e o PDF.

O PDF NAO e gerado a partir do JSON bruto. O contrato canonico e primeiro
traduzido para este modelo, que descreve o documento em secoes, campos e
tabelas ja formatados para leitura humana - e nada mais. Trocar o template do
PDF, ou acrescentar outro formato de saida, nao exige mexer no mapeamento.

O modelo e imutavel de proposito: depois de montado, nenhum template altera o
conteudo do documento.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: Chave do template generico, usado quando o produto nao tem template proprio.
TEMPLATE_PADRAO = "proposta_credito"


@dataclass(frozen=True)
class Campo:
    """Par rotulo/valor de uma secao. ``valor`` ja vem formatado como texto."""

    rotulo: str
    valor: str


@dataclass(frozen=True)
class Secao:
    """Agrupamento de campos com um titulo (CLIENTE, IMOVEL, DECISAO...)."""

    titulo: str
    campos: tuple[Campo, ...]

    @property
    def vazia(self) -> bool:
        return not self.campos


@dataclass(frozen=True)
class Tabela:
    """Dados tabulares do documento, como o cronograma de parcelas."""

    titulo: str
    colunas: tuple[str, ...]
    linhas: tuple[tuple[str, ...], ...]
    observacao: str | None = None

    @property
    def vazia(self) -> bool:
        return not self.linhas


@dataclass(frozen=True)
class ModeloDocumental:
    """Documento pronto para ser renderizado por um template."""

    titulo: str
    tipo_documento: str
    id_operacao: str
    versao_schema: str
    chave_template: str = TEMPLATE_PADRAO
    secoes: tuple[Secao, ...] = ()
    tabelas: tuple[Tabela, ...] = ()
    #: Numeros que merecem destaque visual no topo do documento. Quem decide
    #: QUAIS e o mapeador, que conhece os dados; quem decide COMO exibir e o
    #: template. Um template pode ignorar os destaques.
    destaques: tuple[Campo, ...] = ()
    observacoes: tuple[str, ...] = ()
    pendencias: tuple[str, ...] = field(default=())

    @property
    def secoes_preenchidas(self) -> tuple[Secao, ...]:
        return tuple(secao for secao in self.secoes if not secao.vazia)

    @property
    def tabelas_preenchidas(self) -> tuple[Tabela, ...]:
        return tuple(tabela for tabela in self.tabelas if not tabela.vazia)
