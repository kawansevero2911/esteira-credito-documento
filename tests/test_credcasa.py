import json
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
DADOS = json.loads((ROOT/'exemplos'/'credcasa_proposta_exemplo.json').read_text(encoding='utf-8'))

def test_credcasa_offline_gera_pdf_metadados_evento(client, storage):
    resposta = client.post('/api/documentos/credcasa', json=DADOS)
    assert resposta.status_code == 201, resposta.text
    doc = resposta.json()['documento_id']
    pdf = client.get(f'/api/documentos/{doc}/pdf')
    assert pdf.status_code == 200
    assert pdf.content.startswith(b'%PDF')
    meta = client.get(f'/api/documentos/{doc}')
    assert meta.status_code == 200
    assert meta.json()['id_operacao'] == 'FIN-EXEMPLO-001'
    assert (storage/'eventos'/'eventos.jsonl').exists()

def test_credcasa_invalido(client):
    assert client.post('/api/documentos/credcasa', json={'id':''}).status_code == 400

def test_credcasa_get_mock(client):
    with patch('src.app.consultar_credcasa', return_value=DADOS) as consulta:
        resposta = client.post('/api/documentos/credcasa/FIN-EXEMPLO-001/consultar')
    assert resposta.status_code == 201, resposta.text
    consulta.assert_called_once_with('FIN-EXEMPLO-001')

def test_schema_credcasa(client):
    assert client.get('/api/schemas/credcasa').status_code == 200
