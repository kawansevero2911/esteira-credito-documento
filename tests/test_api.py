import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import processo
from src.api import app

client = TestClient(app)
BASE = Path(__file__).resolve().parents[1]


@pytest.fixture
def storage_temporario(tmp_path, monkeypatch):
    monkeypatch.setattr(processo, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(processo, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(processo, "DOCUMENTOS_DIR", tmp_path / "documentos")
    monkeypatch.setattr(processo, "EVENTOS_DIR", tmp_path / "eventos")
    return tmp_path


def _exemplo(nome: str) -> dict:
    return json.loads((BASE / "examples" / nome).read_text(encoding="utf-8"))


# ---------------------------------------------------------------- endpoints

def test_saude():
    response = client.get("/api/saude")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "servico": "estruturacao-documentos"}


def test_criar_documento_valido(storage_temporario):
    response = client.post("/api/documentos", json=_exemplo("operacao_valida.json"))
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "sucesso"
    assert body["documento_id"]
    assert body["evento"]["evento"] == "documento.gerado"
    assert (storage_temporario / "pdfs" / "OP-2026-000123.pdf").exists()


def test_rejeitar_documento_invalido(storage_temporario):
    response = client.post("/api/documentos", json=_exemplo("operacao_invalida.json"))
    assert response.status_code == 400
    body = response.json()
    assert body["codigo"] == "DADOS_INVALIDOS"
    assert body["detalhes"]
    assert not (storage_temporario / "pdfs").exists()


def test_consultar_documento_criado(storage_temporario):
    criado = client.post("/api/documentos", json=_exemplo("operacao_valida.json")).json()
    response = client.get(f"/api/documentos/{criado['documento_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["_id"] == criado["documento_id"]
    assert body["id_operacao"] == "OP-2026-000123"
    assert body["criado_em"]


def test_consultar_documento_inexistente(storage_temporario):
    response = client.get("/api/documentos/nao-existe")
    assert response.status_code == 404
    assert response.json() == {"detail": "Documento não encontrado."}


# ---------------------------------------------------------------- Swagger / OpenAPI

def test_swagger_ui_disponivel():
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


def test_redoc_disponivel():
    assert client.get("/redoc").status_code == 200


def test_raiz_redireciona_para_docs():
    response = client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/docs"


def test_openapi_documenta_todos_os_endpoints():
    spec = client.get("/openapi.json").json()
    assert set(spec["paths"]) == {
        "/api/saude",
        "/api/documentos",
        "/api/documentos/{documento_id}",
    }
    for caminho, metodos in spec["paths"].items():
        for metodo, operacao in metodos.items():
            assert operacao.get("summary"), f"{metodo.upper()} {caminho} sem summary"
            assert operacao.get("description"), f"{metodo.upper()} {caminho} sem description"
            assert operacao.get("tags"), f"{metodo.upper()} {caminho} sem tag"


def test_openapi_usa_json_schema_do_contrato():
    spec = client.get("/openapi.json").json()
    contrato = json.loads((BASE / "schemas" / "operacao_credito.schema.json").read_text(encoding="utf-8"))
    componente = spec["components"]["schemas"]["OperacaoCredito"]
    assert componente["required"] == contrato["required"]
    assert componente["properties"] == contrato["properties"]

    corpo = spec["paths"]["/api/documentos"]["post"]["requestBody"]["content"]["application/json"]
    assert corpo["schema"] == {"$ref": "#/components/schemas/OperacaoCredito"}
    assert set(corpo["examples"]) == {"operacao_valida", "operacao_invalida"}


def test_openapi_documenta_respostas_de_erro():
    spec = client.get("/openapi.json").json()
    post = spec["paths"]["/api/documentos"]["post"]["responses"]
    assert {"201", "400"} <= set(post)
    get = spec["paths"]["/api/documentos/{documento_id}"]["get"]["responses"]
    assert {"200", "404"} <= set(get)
    for nome in ("DocumentoCriado", "DocumentoMetadados", "ErroDadosInvalidos", "ErroNaoEncontrado"):
        assert nome in spec["components"]["schemas"]
