"""Tarefa BPMN: "Gerar documento" (PDF com ReportLab)."""
from __future__ import annotations
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def gerar_pdf(dados: dict, caminho_saida: str | Path) -> Path:
    caminho = Path(caminho_saida)
    caminho.parent.mkdir(parents=True, exist_ok=True)

    c = canvas.Canvas(str(caminho), pagesize=A4)
    _, altura = A4
    y = altura - 3 * cm

    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, dados["titulo"])
    y -= 1.4 * cm

    c.setFont("Helvetica", 11)
    linhas = [
        f"ID da operação: {dados['id_operacao']}",
        f"Produto: {dados['tipo_produto']}",
        f"Cliente: {dados['nome_cliente']}",
        f"Documento: {dados['documento_cliente']}",
        f"Valor: {dados['valor_formatado']}",
        f"Prazo: {dados['prazo_meses']} meses",
        f"Taxa de juros: {dados['taxa_formatada']}",
    ]
    for linha in linhas:
        c.drawString(2 * cm, y, linha)
        y -= 0.8 * cm

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(2 * cm, 2 * cm, f"Documento emitido em {dados['emitido_em']} - Esteira de Crédito")

    c.showPage()
    c.save()
    return caminho
