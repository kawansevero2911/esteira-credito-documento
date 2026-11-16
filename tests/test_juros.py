import copy
import json
from pathlib import Path
from src.integracao_juros import validar_juros, JurosErro
import pytest
ROOT=Path(__file__).resolve().parent.parent

def exemplo():
    return json.loads((ROOT/'exemplos/juros_operacao_completa.json').read_text(encoding='utf-8'))

def schema():
    return json.loads((ROOT/'schemas/v1/juros_operacao.schema.json').read_text(encoding='utf-8'))

def test_juros_post_gera_pdf_e_metadados(client,storage):
    r=client.post('/api/documentos/juros',json=exemplo())
    assert r.status_code==201,r.text
    data=r.json()
    assert data['quantidade_parcelas']==12
    m=client.get('/api/documentos/'+data['documento_id'])
    assert m.status_code==200
    assert m.json()['origem']=='juros'
    assert m.json()['versao_schema']=='v1'
    pdf=client.get(data['url_pdf'])
    assert pdf.status_code==200
    assert pdf.content.startswith(b'%PDF')
    assert b'52998224725' not in pdf.content

def test_juros_json_invalido_nao_gera_arquivo(client,storage):
    e=exemplo();e['simulacoes']['PRICE']['cronograma'][0]['vencimento']='2026-99-99'
    r=client.post('/api/documentos/juros',json=e)
    assert r.status_code==400
    assert not list((storage/'pdfs').glob('*.pdf')) if (storage/'pdfs').exists() else True

def test_juros_sistema_ausente(client):
    e=exemplo();e['definicao']['sistema']='SAC';del e['simulacoes']['SAC']
    assert client.post('/api/documentos/juros',json=e).status_code==400

def test_juros_exemplo_12_parcelas_por_sistema():
    e=exemplo();validar_juros(e,schema())
    assert all(len(s['cronograma'])==12 for s in e['simulacoes'].values())
    assert e['simulacoes']['PRICE']['totalPago']==11242.88
