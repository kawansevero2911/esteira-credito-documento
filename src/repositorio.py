from __future__ import annotations
import json
import os
import uuid
from datetime import datetime, timezone


class RepositorioDocumentos:
    """Persistência local orientada a documentos para o protótipo."""

    def __init__(self, diretorio: str):
        self.diretorio = diretorio
        os.makedirs(self.diretorio, exist_ok=True)

    def salvar(self, metadados: dict) -> str:
        doc_id = str(uuid.uuid4())
        registro = {
            "_id": doc_id,
            "criado_em": datetime.now(timezone.utc).isoformat(),
            **metadados,
        }
        caminho = os.path.join(self.diretorio, f"{doc_id}.json")
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(registro, arquivo, ensure_ascii=False, indent=2)
        return doc_id

    def buscar(self, doc_id: str) -> dict | None:
        caminho = os.path.join(self.diretorio, f"{doc_id}.json")
        if not os.path.exists(caminho):
            return None
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
