"""Template da proposta de financiamento imobiliario.

Diferenca em relacao ao template generico: os numeros centrais do financiamento
(valor do imovel, entrada, valor financiado, prazo, taxa e sistema de
amortizacao) aparecem em destaque no topo, antes das secoes detalhadas, porque
sao o que se procura primeiro nesse tipo de proposta.

Os valores destacados vem prontos do modelo documental, em ``destaques``. O
template nao le o JSON da operacao e nao calcula nada.
"""
from __future__ import annotations

from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

from ..modelo_documental import Campo, ModeloDocumental
from . import base

CHAVE = "proposta_imobiliaria"
DESCRICAO = "Proposta de financiamento imobiliário — com painel de destaques."

#: Quantidade de destaques por linha do painel.
COLUNAS_DESTAQUE = 3


def _painel_destaques(destaques: tuple[Campo, ...], estilo: dict) -> list:
    if not destaques:
        return []

    elementos: list = []
    for inicio in range(0, len(destaques), COLUNAS_DESTAQUE):
        faixa = destaques[inicio : inicio + COLUNAS_DESTAQUE]
        rotulos = [Paragraph(campo.rotulo, estilo["destaqueRotulo"]) for campo in faixa]
        valores = [Paragraph(campo.valor, estilo["destaqueValor"]) for campo in faixa]
        # Completa a linha para que as colunas fiquem alinhadas entre as faixas.
        while len(rotulos) < COLUNAS_DESTAQUE:
            rotulos.append(Paragraph("", estilo["destaqueRotulo"]))
            valores.append(Paragraph("", estilo["destaqueValor"]))

        largura = base.LARGURA_UTIL / COLUNAS_DESTAQUE
        painel = Table(
            [rotulos, valores],
            colWidths=[largura] * COLUNAS_DESTAQUE,
            hAlign="LEFT",
        )
        painel.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), base.COR_FUNDO_SECAO),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, 0), 6),
                    ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
                    ("BOX", (0, 0), (-1, -1), 0.25, base.COR_LINHA),
                    ("LINEBEFORE", (1, 0), (-1, -1), 0.25, base.COR_LINHA),
                ]
            )
        )
        elementos += [painel, Spacer(1, 0.2 * cm)]

    elementos.append(Spacer(1, 0.2 * cm))
    return elementos


def montar(modelo: ModeloDocumental) -> list:
    estilo = base.estilos()
    elementos = base.cabecalho(modelo, estilo)
    elementos += _painel_destaques(modelo.destaques, estilo)
    for secao_modelo in modelo.secoes_preenchidas:
        elementos += base.secao(secao_modelo, estilo)
    for tabela_modelo in modelo.tabelas_preenchidas:
        elementos += base.tabela(tabela_modelo, estilo)
    elementos += base.rodape(modelo, estilo)
    return elementos
