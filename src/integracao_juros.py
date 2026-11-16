"""Recebe JSON do grupo Juros SEM rede publica: arquivo ou POST local."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path
from html import escape
from jsonschema import Draft202012Validator, FormatChecker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, LongTable, TableStyle
from .privacidade import mascarar_documento

class JurosErro(Exception):
    pass

def validar_juros(dados: dict, schema: dict) -> None:
    if not isinstance(dados, dict):
        raise JurosErro('O JSON de Juros deve ser um objeto')
    erros = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dados), key=lambda e: str(e.path))
    if erros:
        raise JurosErro('JSON inválido: ' + '; '.join(f'{".".join(map(str, e.path)) or "raiz"}: {e.message}' for e in erros[:8]))
    sistema = dados['definicao']['sistema']
    if sistema not in dados['simulacoes']:
        raise JurosErro('Sistema definido não está presente nas simulações')
    for nome, sim in dados['simulacoes'].items():
        numeros = [p['numero'] for p in sim['cronograma']]
        if numeros != list(range(1, len(numeros)+1)):
            raise JurosErro(f'Cronograma {nome} tem numeração de parcelas inválida')

def _dinheiro(valor):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return 'Não informado'
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')

def gerar_pdf_juros(dados: dict, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    p = lambda value: Paragraph(escape(str(value if value is not None else 'Não informado')), normal)
    doc = SimpleDocTemplate(str(destino), pagesize=A4, leftMargin=1.6*cm, rightMargin=1.6*cm, topMargin=1.6*cm, bottomMargin=1.6*cm)
    fluxo = [Paragraph('Demonstrativo de Cálculo de Juros', styles['Title']), Spacer(1, 12),
             p('Documento informativo. Valores reproduzidos do JSON do grupo de Juros, sem recálculo ou aprovação bancária.'), Spacer(1, 12)]
    entrada = dados['entrada']; taxa = dados['taxa']; definicao = dados['definicao']
    campos = [('Operação', dados['identificador']), ('Estado', dados['estado']), ('Sistema definido', definicao['sistema']),
              ('Data da definição', definicao['definidoEm']), ('Cliente', mascarar_documento(dados['cliente']['documento'])),
              ('Tipo de pessoa', dados['cliente']['tipoPessoa']), ('Score', entrada['score']), ('Modalidade', entrada['modalidade']),
              ('Valor', _dinheiro(entrada['valor'])), ('Prazo (meses)', entrada['prazoMeses']),
              ('Faixa de risco', taxa['faixaRisco']), ('Taxa final mensal (%)', taxa['taxaFinalMes']),
              ('Taxa final anual (%)', taxa['taxaFinalAno']), ('Teto aplicado', taxa['tetoAplicado'])]
    tab = LongTable([[p(a),p(b)] for a,b in campos], colWidths=[6.5*cm,10.3*cm],repeatRows=0)
    tab.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.whitesmoke,colors.white]),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    fluxo.extend([tab,Spacer(1,18)])
    for nome,sim in dados['simulacoes'].items():
        fluxo.extend([Paragraph(f'Simulação {escape(nome)}'+(' (selecionada)' if nome == definicao['sistema'] else ''), styles['Heading2']),
                      p(f'Total de juros: {_dinheiro(sim["totalJuros"])} | Total pago em parcelas: {_dinheiro(sim["totalPago"])}'),
                      p(f'CET mensal: {sim["cet"]["mensalPercentual"]}% | CET anual: {sim["cet"]["anualPercentual"]}%'),
                      p(f'IOF: {_dinheiro(sim["encargos"]["iof"]["total"])} | Encargos: {_dinheiro(sim["encargos"]["total"])} | Valor liberado: {_dinheiro(sim["valorLiberado"])}'),Spacer(1,8)])
        linhas=[[p(x) for x in ('Nº','Vencimento','Parcela','Juros','Amortização','Saldo')]]
        for item in sim['cronograma']:
            linhas.append([p(item['numero']),p(item['vencimento']),p(_dinheiro(item['valor'])),p(_dinheiro(item['juros'])),p(_dinheiro(item['amortizacao'])),p(_dinheiro(item['saldoDevedor']))])
        t=LongTable(linhas,colWidths=[0.9*cm,2.6*cm,3.0*cm,3.0*cm,3.4*cm,3.9*cm],repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),0.5,colors.grey),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        fluxo.extend([t,Spacer(1,16)])
    doc.build(fluxo)

def emitir_juros(dados: dict, schema: dict, storage: Path, repositorio, publicador) -> dict:
    validar_juros(dados, schema)
    documento_id=str(uuid.uuid4())
    relativo=Path('pdfs') / f'{documento_id}.pdf'
    destino=storage / relativo
    try:
        gerar_pdf_juros(dados,destino)
        registro=repositorio.salvar(documento_id,{'id_operacao':dados['identificador'],'tipo_produto':dados['entrada']['modalidade'],
            'tipo_documento':'demonstrativo_juros','origem':'juros','quantidade_parcelas':len(dados['simulacoes'][dados['definicao']['sistema']]['cronograma']),
            'versao_schema':'v1','caminho_pdf':str(relativo)})
        evento=publicador.publicar({'evento':'documento.gerado','id_operacao':dados['identificador'],
            'documento_id':documento_id,'caminho_pdf':str(relativo),'origem':'juros','tipo_documento':'demonstrativo_juros','versao_schema':'v1'})
    except Exception:
        # Em caso de falha, não deixa PDF órfão quando o registro falhar.
        destino.unlink(missing_ok=True)
        raise
    return {'documento_id':documento_id,'id_operacao':dados['identificador'],
            'tipo_documento':'demonstrativo_juros','quantidade_parcelas':len(dados['simulacoes'][dados['definicao']['sistema']]['cronograma']),
            'url_pdf':f'/api/documentos/{documento_id}/pdf','evento':evento}
