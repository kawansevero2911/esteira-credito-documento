"""Fixtures compartilhadas pelos testes que usam o pytest."""
from __future__ import annotations

import pytest

from src import processo


@pytest.fixture
def storage_temporario(tmp_path, monkeypatch):
    """Redireciona o armazenamento do processo para uma pasta do teste.

    Sem isso, rodar os testes sujaria storage/ do repositorio.
    """
    monkeypatch.setattr(processo, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(processo, "PDF_DIR", tmp_path / "pdfs")
    monkeypatch.setattr(processo, "DOCUMENTOS_DIR", tmp_path / "documentos")
    monkeypatch.setattr(processo, "EVENTOS_DIR", tmp_path / "eventos")
    return tmp_path
