import json
from pathlib import Path
from unittest.mock import patch
import httpx

ROOT = Path(__file__).resolve().parent.parent
DADOS = json.loads((ROOT / 'exemplos' / 'finops_consulta_exemplo.json').read_text(encoding='utf-8'))

def test_criar_pdf_finops_sem_api(client, storage):
    resposta = client.post('/api/documentos/finops', json=DADOS)
    assert resposta.status_code == 201, resposta.text
    doc_id = resposta.json()['documento_id']
    assert resposta.json()['quantidade_parcelas'] == 3
    pdf = client.get(f'/api/documentos/{doc_id}/pdf')
    assert pdf.status_code == 200
    assert pdf.content[:4] == b'%PDF'
    metadados = client.get(f'/api/documentos/{doc_id}')
    assert metadados.status_code == 200
    assert metadados.json()['id_operacao'] == 'OP-2026-0001'
    assert (storage / 'eventos').exists()

def test_rejeitar_finops_invalido(client):
    resposta = client.post('/api/documentos/finops', json={'operacao':{}, 'parcelas':[]})
    assert resposta.status_code == 400

def test_consulta_get_finops_mock(client):
    with patch('src.app.consultar_finops', return_value=(DADOS['operacao'], DADOS['parcelas'])) as consulta:
        resposta = client.post('/api/documentos/finops/OP-2026-0001/consultar')
    assert resposta.status_code == 201, resposta.text
    consulta.assert_called_once_with('OP-2026-0001')

def test_endpoint_original_preservado(client, operacao_valida):
    assert client.post('/api/documentos', json=operacao_valida).status_code == 201
