"""Emissao do PDF a partir do modelo documental.

O PDF e gerado do MODELO DOCUMENTAL, nunca do JSON recebido: este modulo nao
conhece o contrato de entrada. Sua responsabilidade e escolher o template pela
chave que o mapeador definiu, montar o documento e paginar.

ReportLab continua sendo a biblioteca de geracao, agora pelo Platypus, que
quebra tabelas longas entre paginas e repete o cabecalho - necessario porque um
cronograma de financiamento imobiliario pode passar de 300 parcelas.
"""
from __future__ import annotations

import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate

from .modelo_documental import ModeloDocumental
from .templates_pdf import obter_template

MARGEM = 2 * cm


def _rodape_pagina(canvas, documento) -> None:  # noqa: ANN001
    """Numero da pagina e identificacao, repetidos em todas as folhas."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#5A6675"))
    largura, _ = A4
    canvas.drawRightString(largura - MARGEM, 1.2 * cm, f"Página {canvas.getPageNumber()}")
    rotulo = getattr(documento, "rotuloRodape", "")
    if rotulo:
        canvas.drawString(MARGEM, 1.2 * cm, rotulo)
    canvas.setStrokeColor(colors.HexColor("#D7DEE8"))
    canvas.setLineWidth(0.25)
    canvas.line(MARGEM, 1.55 * cm, largura - MARGEM, 1.55 * cm)
    canvas.restoreState()


def gerar_pdf(modelo: ModeloDocumental, caminho_saida: str) -> str:
    """Gera o PDF do modelo em ``caminho_saida`` e devolve o caminho."""
    diretorio = os.path.dirname(caminho_saida)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)

    documento = SimpleDocTemplate(
        caminho_saida,
        pagesize=A4,
        leftMargin=MARGEM,
        rightMargin=MARGEM,
        topMargin=MARGEM,
        bottomMargin=2.2 * cm,
        title=modelo.titulo,
        author="Esteira de Crédito — Estruturação de Documentos",
        subject=modelo.tipo_documento,
    )
    documento.rotuloRodape = " · ".join(
        parte
        for parte in (
            f"Operação {modelo.id_operacao}" if modelo.id_operacao else "",
            f"Contrato {modelo.versao_schema}" if modelo.versao_schema else "",
        )
        if parte
    )

    montar = obter_template(modelo.chave_template)
    documento.build(montar(modelo), onFirstPage=_rodape_pagina, onLaterPages=_rodape_pagina)
    return caminho_saida
