"""Blocos de montagem compartilhados pelos templates de PDF.

Aqui ficam os estilos e os elementos repetidos (cabecalho, secao de campos,
tabela, rodape de pendencias). Cada template combina esses blocos na ordem que
o seu produto pede, em vez de redesenhar o documento do zero - e e por isso que
acrescentar um produto novo custa um arquivo pequeno.

A montagem usa o Platypus do ReportLab, e nao desenho direto no canvas, porque
o cronograma de parcelas pode ter centenas de linhas: o Platypus quebra a
tabela entre paginas e repete o cabecalho sozinho.
"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

from ..modelo_documental import ModeloDocumental, Secao, Tabela

LARGURA_UTIL = 17 * cm
LARGURA_ROTULO = 6 * cm
LARGURA_VALOR = LARGURA_UTIL - LARGURA_ROTULO

COR_TITULO = colors.HexColor("#1F3A5F")
COR_LINHA = colors.HexColor("#D7DEE8")
COR_FUNDO_SECAO = colors.HexColor("#EEF2F7")
COR_TEXTO_SECUNDARIO = colors.HexColor("#5A6675")

_LARGURAS_PARCELAS = (
    1.2 * cm,
    2.3 * cm,
    2.7 * cm,
    2.9 * cm,
    2.6 * cm,
    3.2 * cm,
    2.1 * cm,
)


def estilos() -> dict[str, ParagraphStyle]:
    """Estilos de paragrafo usados pelos templates."""
    base = getSampleStyleSheet()
    return {
        "titulo": ParagraphStyle(
            "TituloDocumento",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=COR_TITULO,
            spaceAfter=2,
        ),
        "subtitulo": ParagraphStyle(
            "SubtituloDocumento",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=COR_TEXTO_SECUNDARIO,
        ),
        "secao": ParagraphStyle(
            "TituloSecao",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=COR_TITULO,
        ),
        "rotulo": ParagraphStyle(
            "Rotulo",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
        ),
        "valor": ParagraphStyle(
            "Valor",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
        ),
        "celula": ParagraphStyle(
            "Celula",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
        ),
        "celulaCabecalho": ParagraphStyle(
            "CelulaCabecalho",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            textColor=colors.white,
        ),
        "nota": ParagraphStyle(
            "Nota",
            parent=base["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=7.5,
            leading=10,
            textColor=COR_TEXTO_SECUNDARIO,
        ),
        "destaqueRotulo": ParagraphStyle(
            "DestaqueRotulo",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            alignment=TA_CENTER,
            textColor=COR_TEXTO_SECUNDARIO,
        ),
        "destaqueValor": ParagraphStyle(
            "DestaqueValor",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            textColor=COR_TITULO,
        ),
    }


def _escapar(texto: str) -> str:
    """Impede que dado recebido de outro processo seja lido como marcacao."""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def cabecalho(modelo: ModeloDocumental, estilo: dict[str, ParagraphStyle]) -> list:
    """Titulo do documento e a linha de identificacao da operacao."""
    identificacao = " · ".join(
        parte
        for parte in (
            f"Operação {_escapar(modelo.id_operacao)}" if modelo.id_operacao else "",
            _escapar(modelo.tipo_documento) if modelo.tipo_documento else "",
            f"Contrato {_escapar(modelo.versao_schema)}" if modelo.versao_schema else "",
        )
        if parte
    )
    elementos: list = [Paragraph(_escapar(modelo.titulo), estilo["titulo"])]
    if identificacao:
        elementos.append(Paragraph(identificacao, estilo["subtitulo"]))
    elementos.append(Spacer(1, 0.45 * cm))
    return elementos


def secao(secao_modelo: Secao, estilo: dict[str, ParagraphStyle]) -> list:
    """Titulo da secao seguido dos pares rotulo/valor."""
    if secao_modelo.vazia:
        return []

    linhas = [
        [
            Paragraph(_escapar(campo.rotulo), estilo["rotulo"]),
            Paragraph(_escapar(campo.valor), estilo["valor"]),
        ]
        for campo in secao_modelo.campos
    ]
    tabela = Table(linhas, colWidths=[LARGURA_ROTULO, LARGURA_VALOR], hAlign="LEFT")
    tabela.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, -2), 0.25, COR_LINHA),
            ]
        )
    )

    titulo = _faixa_titulo(secao_modelo.titulo, estilo)
    # Mantem o titulo junto das primeiras linhas para nao sobrar titulo solto
    # no fim da pagina.
    return [KeepTogether([titulo, tabela]), Spacer(1, 0.35 * cm)]


def _faixa_titulo(texto: str, estilo: dict[str, ParagraphStyle]) -> Table:
    faixa = Table(
        [[Paragraph(_escapar(texto), estilo["secao"])]],
        colWidths=[LARGURA_UTIL],
        hAlign="LEFT",
    )
    faixa.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COR_FUNDO_SECAO),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, -1), 0.6, COR_TITULO),
            ]
        )
    )
    return faixa


def tabela(tabela_modelo: Tabela, estilo: dict[str, ParagraphStyle]) -> list:
    """Tabela com cabecalho repetido a cada pagina."""
    if tabela_modelo.vazia:
        return []

    cabecalho_linha = [
        Paragraph(_escapar(coluna), estilo["celulaCabecalho"]) for coluna in tabela_modelo.colunas
    ]
    corpo = [
        [Paragraph(_escapar(celula), estilo["celula"]) for celula in linha]
        for linha in tabela_modelo.linhas
    ]

    quantidade = len(tabela_modelo.colunas)
    larguras = (
        list(_LARGURAS_PARCELAS)
        if quantidade == len(_LARGURAS_PARCELAS)
        else [LARGURA_UTIL / quantidade] * quantidade
    )

    grade = Table([cabecalho_linha, *corpo], colWidths=larguras, repeatRows=1, hAlign="LEFT")
    grade.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COR_TITULO),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (-2, -1), "RIGHT"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (-1, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.25, COR_LINHA),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COR_FUNDO_SECAO]),
            ]
        )
    )

    elementos: list = [_faixa_titulo(tabela_modelo.titulo, estilo), Spacer(1, 0.15 * cm), grade]
    if tabela_modelo.observacao:
        elementos += [Spacer(1, 0.15 * cm), Paragraph(_escapar(tabela_modelo.observacao), estilo["nota"])]
    elementos.append(Spacer(1, 0.35 * cm))
    return elementos


def rodape(modelo: ModeloDocumental, estilo: dict[str, ParagraphStyle]) -> list:
    """Observacoes do emissor e informacoes que ainda dependem de outros processos."""
    elementos: list = []

    if modelo.observacoes:
        elementos += _faixa_e_notas("OBSERVAÇÕES", modelo.observacoes, estilo)

    if modelo.pendencias:
        elementos += _faixa_e_notas(
            "INFORMAÇÕES NÃO RECEBIDAS",
            modelo.pendencias,
            estilo,
            nota_final=(
                "Este documento apresenta apenas os dados recebidos dos demais "
                "processos da Esteira de Crédito. Nenhum valor foi calculado ou "
                "estimado por este serviço."
            ),
        )

    return elementos


def _faixa_e_notas(
    titulo: str,
    itens: tuple[str, ...],
    estilo: dict[str, ParagraphStyle],
    nota_final: str | None = None,
) -> list:
    elementos: list = [_faixa_titulo(titulo, estilo), Spacer(1, 0.15 * cm)]
    for item in itens:
        elementos.append(Paragraph(f"• {_escapar(item)}", estilo["nota"]))
    if nota_final:
        elementos += [Spacer(1, 0.1 * cm), Paragraph(_escapar(nota_final), estilo["nota"])]
    elementos.append(Spacer(1, 0.35 * cm))
    return elementos


def documento_completo(modelo: ModeloDocumental, estilo: dict[str, ParagraphStyle]) -> list:
    """Sequencia padrao: cabecalho, secoes na ordem do modelo, tabelas, rodape."""
    elementos = cabecalho(modelo, estilo)
    for secao_modelo in modelo.secoes_preenchidas:
        elementos += secao(secao_modelo, estilo)
    for tabela_modelo in modelo.tabelas_preenchidas:
        elementos += tabela(tabela_modelo, estilo)
    elementos += rodape(modelo, estilo)
    return elementos
