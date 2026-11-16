import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app import create_app

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def storage(tmp_path):
    return tmp_path / "storage"


@pytest.fixture
def client(storage):
    return TestClient(create_app(storage_dir=storage, imprimir_eventos=False))


@pytest.fixture
def operacao_valida():
    return json.loads((RAIZ / "exemplos" / "operacao_valida.json").read_text(encoding="utf-8"))


@pytest.fixture
def operacao_invalida():
    return json.loads((RAIZ / "exemplos" / "operacao_invalida.json").read_text(encoding="utf-8"))


@pytest.fixture
def schema():
    return json.loads((RAIZ / "schemas" / "v1" / "operacao_credito.schema.json").read_text(encoding="utf-8"))
