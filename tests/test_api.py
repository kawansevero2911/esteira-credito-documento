import json
from pathlib import Path
from fastapi.testclient import TestClient

from src.api import app
from src import processo

client = TestClient(app)
BASE = Path(__file__).resolve().parents[1]


def test_saude():
    response = client.get("/api/saude")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_criar_documento_valido(tmp_path, monkeypatch):
    monkeypatch.setattr(processo, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(processo, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(processo, "DOCUMENTOS_DIR", tmp_path / "documentos")
    monkeypatch.setattr(processo, "EVENTOS_DIR", tmp_path / "eventos")

    operacao = json.loads((BASE / "examples" / "operacao_valida.json").read_text(encoding="utf-8"))
    response = client.post("/api/documentos", json=operacao)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "sucesso"
    assert body["documento_id"]
    assert body["evento"]["evento"] == "documento.gerado"


def test_rejeitar_documento_invalido(tmp_path, monkeypatch):
    monkeypatch.setattr(processo, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(processo, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(processo, "DOCUMENTOS_DIR", tmp_path / "documentos")
    monkeypatch.setattr(processo, "EVENTOS_DIR", tmp_path / "eventos")

    operacao = json.loads((BASE / "examples" / "operacao_invalida.json").read_text(encoding="utf-8"))
    response = client.post("/api/documentos", json=operacao)
    assert response.status_code == 400
    body = response.json()
    assert body["codigo"] == "DADOS_INVALIDOS"
