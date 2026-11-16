"""Regressão das correções da avaliação técnica."""
import json
from pathlib import Path
import pytest
from src.privacidade import mascarar_documento
from src.validador import ErroValidacao, validar_operacao
from src.integracao_finops import validar_finops, FinOpsErro, gerar_demonstrativo
from src.integracao_credcasa import _moeda
from src.app import BASE_DIR


def test_mascara_cpf_e_cnpj():
    assert mascarar_documento('52998224725') == '***.982.247-**'
    assert mascarar_documento('529.982.247-25') == '***.982.247-**'
    assert mascarar_documento('12.345.678/0001-90') == '**.345.678/****-**'


def test_get_metadados_extras(client, operacao_valida):
    criado = client.post('/api/documentos', json=operacao_valida).json()
    dado = client.get('/api/documentos/' + criado['documento_id']).json()
    assert dado['tipo_documento'] == 'PROPOSTA_CREDITO'
    assert dado['origem'] == 'OPERACAO_CREDITO'
    assert dado['versao_schema'] == 'v1'


def test_finops_rejeita_data_invalida():
    dados = json.loads((BASE_DIR / 'exemplos/finops_consulta_exemplo.json').read_text(encoding='utf-8'))
    schema = json.loads((BASE_DIR / 'schemas/v1/finops_consulta.schema.json').read_text(encoding='utf-8'))
    dados['parcelas'][0]['vencimento'] = '2026-02-30'
    with pytest.raises(FinOpsErro):
        validar_finops(dados['operacao'], dados['parcelas'], schema)


def test_finops_pdf_escapa_marcacao(tmp_path):
    dados = json.loads((BASE_DIR / 'exemplos/finops_consulta_exemplo.json').read_text(encoding='utf-8'))
    dados['operacao']['produto']['nome'] = 'Crédito <b>pessoal & teste'
    saida = tmp_path / 'seguro.pdf'
    gerar_demonstrativo(dados['operacao'], dados['parcelas'], saida)
    assert saida.read_bytes().startswith(b'%PDF')


def test_moeda_credcasa_nao_escapa_duas_vezes():
    assert _moeda('R$ <teste>') == 'R$ <teste>'


def test_swagger_integracoes(client):
    spec = client.get('/openapi.json').json()
    for caminho in ['/api/documentos/finops', '/api/documentos/credcasa']:
        post = spec['paths'][caminho]['post']
        assert '201' in post['responses'] and '400' in post['responses']
        assert 'schema' in post['responses']['201']['content']['application/json']
    for caminho in ['/api/documentos/finops/{identificador}/consultar', '/api/documentos/credcasa/{identificador}/consultar']:
        assert '502' in spec['paths'][caminho]['post']['responses']
