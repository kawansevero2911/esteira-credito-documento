"""Adaptador somente leitura para FinOps; não altera outros serviços."""
from __future__ import annotations
import os
import uuid
from html import escape
from urllib.parse import quote
from datetime import datetime, timezone
from pathlib import Path
import httpx
from jsonschema import Draft202012Validator, FormatChecker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .mapeador import formatar_moeda
from .privacidade import mascarar_documento

class FinOpsErro(Exception):
    pass


def validar_finops(operacao: dict, parcelas: list, schema: dict):
    validador = Draft202012Validator(schema, format_checker=FormatChecker())
    erros = []
    for erro in validador.iter_errors({"operacao": operacao, "parcelas": parcelas}):
        erros.append({"campo": '.'.join(map(str, erro.absolute_path)) or "raiz", "mensagem": erro.message})
    if erros:
        raise FinOpsErro(f"JSON do FinOps inválido: {erros}")


def consultar_finops(identificador: str, base_url: str | None = None):
    if not identificador or len(identificador) > 150 or '/' in identificador or '..' in identificador:
        raise FinOpsErro('Identificador inválido')
    base = (base_url or os.environ.get('FINOPS_URL', 'http://localhost:8083')).rstrip('/')
    try:
        with httpx.Client(timeout=12.0) as cliente:
            resposta = cliente.get(f'{base}/operacoes/{quote(identificador, safe="")}')
            resposta.raise_for_status()
            operacao = resposta.json()
            resposta = cliente.get(f'{base}/operacoes/{quote(identificador, safe="")}/parcelas')
            resposta.raise_for_status()
            parcelas = resposta.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FinOpsErro(f'Não foi possível consultar FinOps: {exc}') from exc
    if not isinstance(operacao, dict) or not isinstance(parcelas, list):
        raise FinOpsErro('FinOps retornou formato inesperado')
    if operacao.get('numeroOperacao') != identificador:
        raise FinOpsErro('Identificador da resposta não corresponde ao solicitado')
    return operacao, parcelas


def percentual(decimal):
    return f'{float(decimal)*100:.2f}'.replace('.', ',') + '%'


def gerar_demonstrativo(operacao: dict, parcelas: list, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(caminho), pagesize=A4, rightMargin=1.7*cm, leftMargin=1.7*cm,
                            topMargin=1.8*cm, bottomMargin=1.8*cm)
    def p(text):
        return Paragraph(escape(str(text)), styles['Normal'])
    def linha(chave, valor):
        return [p(chave), p(valor)]
    cond = operacao['condicoesFinanceiras']
    enc = operacao.get('encargos', {})
    cet = operacao.get('cet', {})
    produto = operacao['produto']
    corpo = [Paragraph('Demonstrativo financeiro da operação', styles['Title']), Spacer(1, 12),
             p('Documento informativo gerado a partir de dados consultados no FinOps. Não constitui contrato.'), Spacer(1, 14)]
    infos = [
        linha('Operação', operacao['numeroOperacao']),
        linha('Cliente (documento)', mascarar_documento(operacao['clienteId'])),
        linha('Pessoa', operacao['tipoPessoa']),
        linha('Produto', produto.get('nome', produto['codigo'])),
        linha('Status', operacao['status']),
        linha('Valor aprovado', formatar_moeda(cond['valorAprovado'])),
        linha('Valor liberado', formatar_moeda(operacao.get('valorLiberado', cond['valorAprovado']))),
        linha('Prazo', f"{cond['prazoMeses']} meses"),
        linha('Amortização', cond['sistemaAmortizacao']),
        linha('Juros mensais', percentual(cond['taxaJuros'])),
        linha('Juros anuais', percentual(cond['taxaJurosAnual']) if 'taxaJurosAnual' in cond else 'Não informado'),
        linha('CET mensal', percentual(cet['mensal']) if 'mensal' in cet else 'Não informado'),
        linha('CET anual', percentual(cet['anual']) if 'anual' in cet else 'Não informado'),
        linha('Encargos totais', formatar_moeda(enc['total']) if 'total' in enc else 'Não informado'),
        linha('Primeiro vencimento', cond['primeiroVencimento']),
    ]
    tabela = Table(infos, colWidths=[5.4*cm, 11.1*cm], hAlign='LEFT')
    tabela.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'), ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.whitesmoke, colors.white]), ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    corpo += [tabela, Spacer(1, 16), Paragraph('Cronograma de parcelas', styles['Heading2'])]
    linhas = [[p('Nº'), p('Vencimento'), p('Parcela'), p('Juros'), p('Amortização'), p('Saldo')]]
    for parcela in parcelas:
        linhas.append([p(parcela['numero']), p(parcela['vencimento']), p(formatar_moeda(parcela['valorParcela'])),
                       p(formatar_moeda(parcela['juros'])), p(formatar_moeda(parcela['amortizacao'])),
                       p(formatar_moeda(parcela['saldoDevedor']))])
    tabela_parcelas = Table(linhas, colWidths=[0.9*cm, 3.0*cm, 3.15*cm, 2.7*cm, 3.5*cm, 3.25*cm], repeatRows=1)
    tabela_parcelas.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dce9f8')),
                                        ('VALIGN',(0,0),(-1,-1),'TOP'), ('LINEBELOW',(0,0),(-1,0),0.6,colors.grey),
                                        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.whitesmoke]),
                                        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    corpo.append(tabela_parcelas)
    corpo += [Spacer(1, 12), p(f'Parcelas recebidas para este documento: {len(parcelas)}.'),
              p('Emitido em UTC: ' + datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M'))]
    doc.build(corpo)


def emitir_finops(operacao, parcelas, schema, storage, repositorio, publicador):
    validar_finops(operacao, parcelas, schema)
    documento_id = str(uuid.uuid4())
    caminho_relativo = f'pdfs/{documento_id}.pdf'
    gerar_demonstrativo(operacao, parcelas, Path(storage) / caminho_relativo)
    repositorio.salvar(documento_id, {
        'id_operacao': operacao['numeroOperacao'],
        'tipo_produto': operacao['produto']['codigo'],
        'tipo_documento': 'DEMONSTRATIVO_FINANCEIRO',
        'origem': 'FINOPS',
        'versao_schema': 'v1',
        'quantidade_parcelas': len(parcelas),
        'caminho_pdf': caminho_relativo,
    })
    evento = publicador.publicar({'evento': 'documento.gerado', 'id_operacao': operacao['numeroOperacao'],
                                  'documento_id': documento_id, 'caminho_pdf': caminho_relativo,
                                  'tipo_documento': 'DEMONSTRATIVO_FINANCEIRO', 'origem': 'FINOPS', 'versao_schema': 'v1'})
    return {'documento_id': documento_id, 'id_operacao': operacao['numeroOperacao'],
            'tipo_documento': 'DEMONSTRATIVO_FINANCEIRO', 'quantidade_parcelas': len(parcelas), 'evento': evento,
            'url_pdf': f'/api/documentos/{documento_id}/pdf'}
