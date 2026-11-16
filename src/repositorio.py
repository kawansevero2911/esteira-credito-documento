"""Tarefa BPMN: "Armazenar documento" (base orientada a documentos).

`RepositorioDocumentos` é a PORTA (interface). `RepositorioArquivo` é um adaptador
que guarda cada documento como JSON em disco. Trocar por MongoDB = novo adaptador
com os mesmos dois métodos, sem alterar o processo.
"""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


class RepositorioDocumentos(Protocol):
    def salvar(self, documento_id: str, metadados: dict) -> dict: ...
    def buscar(self, documento_id: str) -> dict | None: ...


def id_documento_valido(documento_id: str) -> bool:
    """Aceita só UUID canônico (evita path traversal em buscas vindas da API)."""
    try:
        return str(uuid.UUID(documento_id)) == documento_id
    except (ValueError, AttributeError, TypeError):
        return False


class RepositorioArquivo:
    def __init__(self, diretorio_base: str | Path):
        self.diretorio = Path(diretorio_base) / "documentos"
        self.diretorio.mkdir(parents=True, exist_ok=True)

    def salvar(self, documento_id: str, metadados: dict) -> dict:
        registro = {
            "_id": documento_id,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            **metadados,
        }
        with open(self.diretorio / f"{documento_id}.json", "w", encoding="utf-8") as f:
            json.dump(registro, f, ensure_ascii=False, indent=2)
        return registro

    def buscar(self, documento_id: str) -> dict | None:
        if not id_documento_valido(documento_id):
            return None
        caminho = self.diretorio / f"{documento_id}.json"
        if not caminho.exists():
            return None
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)


class RepositorioMongoDB:
    """Adaptador MongoDB para persistir metadados dos documentos.

    Os PDFs continuam no armazenamento de arquivos; o MongoDB guarda os
    metadados e o caminho do PDF, mantendo o contrato da porta RepositorioDocumentos.
    """

    def __init__(self, uri: str, banco: str = "esteira_credito", colecao: str = "documentos",
                 cliente=None):
        if cliente is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:  # pragma: no cover - depende da instalação
                raise RuntimeError("Instale pymongo para utilizar o MongoDB: pip install pymongo") from exc
            cliente = MongoClient(uri, serverSelectionTimeoutMS=5000)

        self.cliente = cliente
        self.banco = self.cliente[banco]
        self.colecao = self.banco[colecao]
        # Falha cedo se a configuração estiver incorreta ou o banco indisponível.
        self.cliente.admin.command("ping")

    def salvar(self, documento_id: str, metadados: dict) -> dict:
        registro = {
            "_id": documento_id,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            **metadados,
        }
        self.colecao.insert_one(registro.copy())
        return registro

    def buscar(self, documento_id: str) -> dict | None:
        if not id_documento_valido(documento_id):
            return None
        return self.colecao.find_one({"_id": documento_id})

    def fechar(self) -> None:
        self.cliente.close()
