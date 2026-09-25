from __future__ import annotations
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def gerar_pdf(dados_template: dict, caminho_saida: str) -> str:
    diretorio = os.path.dirname(caminho_saida)
    if diretorio:
        os.makedirs(diretorio, exist_ok=True)
    c = canvas.Canvas(caminho_saida, pagesize=A4)
    _, altura = A4
    y = altura - 3 * cm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, dados_template["titulo"])
    y -= 1.2 * cm
    c.setFont("Helvetica", 11)
    linhas = [
        f"ID da operação: {dados_template['id_operacao']}",
        f"Produto: {dados_template['tipo_produto']}",
        f"Cliente: {dados_template['nome_cliente']}",
        f"Documento: {dados_template['documento_cliente']}",
        f"Valor: {dados_template['valor_formatado']}",
        f"Prazo: {dados_template['prazo_meses']} meses",
        f"Taxa de juros: {dados_template['taxa_formatada']}",
    ]
    for linha in linhas:
        c.drawString(2 * cm, y, linha)
        y -= 0.8 * cm
    c.showPage()
    c.save()
    return caminho_saida
