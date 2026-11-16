"""Adaptador de leitura CredCasa. Não altera dados nem chama endpoints de escrita."""
from __future__ import annotations
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from html import escape
from .privacidade import mascarar_documento
from urllib.parse import quote
import httpx
from jsonschema import Draft202012Validator, FormatChecker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

class CredCasaErro(Exception):
    pass


def consultar_credcasa(identificador: str, base_url: str | None = None) -> dict:
    if not identificador or len(identificador) > 150 or '/' in identificador or '..' in identificador:
        raise CredCasaErro('Identificador inválido')
    base = (base_url or os.getenv('CREDCASA_URL', 'https://credcasa-esteira-credito.onrender.com')).rstrip('/')
    try:
        with httpx.Client(timeout=25.0, follow_redirects=False) as client:
            response = client.get(f'{base}/api/esteira/{quote(identificador, safe="")}')
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise CredCasaErro(f'Falha na consulta ao CredCasa: {exc}') from exc
    if not isinstance(data, dict):
        raise CredCasaErro('Resposta do CredCasa não é um objeto JSON')
    return data


def validar_credcasa(dados: dict, schema: dict):
    if not isinstance(dados, dict):
        raise CredCasaErro('A proposta precisa ser um objeto JSON')
    erros = sorted(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(dados), key=lambda e: str(e.path))
    if erros:
        raise CredCasaErro('JSON inválido: ' + '; '.join(f'{".".join(map(str,e.path)) or "raiz"}: {e.message}' for e in erros[:8]))


def _texto(valor):
    if valor is None or valor == '':
        return 'Não informado'
    if isinstance(valor, (dict, list)):
        return 'Informação estruturada (consultar JSON de origem)'
    return escape(str(valor))


def _moeda(valor):
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return str(valor) if valor is not None else 'Não informado'
    return 'R$ ' + f'{valor:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _buscar(dados, *caminhos):
    for caminho in caminhos:
        atual = dados
        for chave in caminho.split('.'):
            if not isinstance(atual, dict) or chave not in atual:
                atual = None
                break
            atual = atual[chave]
        if atual is not None:
            return atual
    return None


def gerar_pdf_credcasa(dados: dict, caminho: Path):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    normal = styles['Normal']
    doc = SimpleDocTemplate(str(caminho), pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.7*cm, bottomMargin=1.7*cm)
    p = lambda x: Paragraph(_texto(x), normal)
    linhas = [
        ('Identificador', _buscar(dados,'id','identificador','proposta.id')),
        ('Data de criação', _buscar(dados,'createdAt','criadoEm','dataCriacao')),
        ('Situação da proposta', _buscar(dados,'status','decisao.status')),
        ('Cliente', _buscar(dados,'cliente.nome','cliente','nomeCliente')),
        ('CPF', mascarar_documento(_buscar(dados,'cpf','cliente.cpf','cliente.documento'))),
        ('Tipo do imóvel', _buscar(dados,'tipo','imovel.tipo')),
        ('Endereço', _buscar(dados,'endereco','imovel.endereco')),
        ('Cidade', _buscar(dados,'cidade','imovel.cidade')),
        ('Estado', _buscar(dados,'estado','imovel.estado')),
        ('Valor do imóvel', _moeda(_buscar(dados,'imovel.valor','imovel','valorImovel'))),
        ('Entrada', _moeda(_buscar(dados,'entrada','valorEntrada'))),
        ('Valor financiado', _moeda(_buscar(dados,'principal','valorFinanciado'))),
        ('Prazo (meses)', _buscar(dados,'prazo','prazoMeses')),
        ('Juros mensais (%)', _buscar(dados,'taxa','taxaJurosMensal')),
        ('Amortização', _buscar(dados,'sistema','sistemaAmortizacao')),
        ('Comprometimento da renda (%)', _buscar(dados,'comprometimento')),
        ('Score', _buscar(dados,'score','score.scoreFinal','contextoScore.scoreFinal')),
        ('Decisão', _buscar(dados,'decisao.resultado','decisao','status')),
    ]
    corpo = [Paragraph('Proposta de financiamento imobiliário', styles['Title']), Spacer(1, 12),
             p('Resumo informativo gerado a partir do JSON fornecido pelo CredCasa. Não constitui contrato ou aprovação bancária.'), Spacer(1, 14)]
    tabela = Table([[p(k),p(v)] for k,v in linhas], colWidths=[6.5*cm, 9.5*cm], hAlign='LEFT')
    tabela.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'), ('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.whitesmoke,colors.white]), ('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    corpo.append(tabela)
    # Preserva as integrações recebidas sem presumir formato não confirmado.
    presentes = [chave for chave in ('integracoes','juros','operacoes','parcelas','motivos','score','decisao') if chave in dados]
    if presentes:
        corpo.extend([Spacer(1,12),Paragraph('Informações adicionais recebidas', styles['Heading2']),
                      p('Blocos presentes no JSON original: ' + ', '.join(presentes) + '. Os dados completos permanecem na origem; não foram recalculados.')])
    corpo.extend([Spacer(1,12),p('Documento emitido em UTC: '+datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M'))])
    doc.build(corpo)


def emitir_credcasa(dados: dict, schema: dict, storage: Path, repositorio, publicador):
    validar_credcasa(dados, schema)
    doc_id = str(uuid.uuid4())
    id_proposta = str(_buscar(dados,'id','identificador','proposta.id'))
    relativo = f'pdfs/{doc_id}.pdf'
    gerar_pdf_credcasa(dados, Path(storage)/relativo)
    repositorio.salvar(doc_id, {'id_operacao':id_proposta, 'tipo_produto':'FINANCIAMENTO_IMOBILIARIO',
                                'tipo_documento':'PROPOSTA_IMOBILIARIA','origem':'CREDCASA','versao_schema':'v1','caminho_pdf':relativo})
    evento = publicador.publicar({'evento':'documento.gerado','id_operacao':id_proposta,'documento_id':doc_id,'caminho_pdf':relativo,'tipo_documento':'PROPOSTA_IMOBILIARIA',
                                 'origem':'CREDCASA','versao_schema':'v1'})
    return {'documento_id':doc_id,'id_operacao':id_proposta,'tipo_documento':'PROPOSTA_IMOBILIARIA','evento':evento,
            'url_pdf':f'/api/documentos/{doc_id}/pdf'}
