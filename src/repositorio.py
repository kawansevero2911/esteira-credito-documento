"""Persistencia dos metadados documentais.

O armazenamento continua local, em arquivos JSON, um por documento - e o que o
projeto usa desde a versao 1.0.0 e o suficiente para esta etapa. O que mudou e
que agora existe uma INTERFACE (``RepositorioDocumentos``) separada da
implementacao (``RepositorioArquivosJson``): o resto do sistema depende da
interface, entao trocar o arquivo por MongoDB ou por outra base orientada a
documentos e escrever uma classe nova, sem tocar no fluxo.

O registro e modelado como documento, e nao como linha de tabela: chave propria,
campos aninhados e ausencia de esquema fixo entre registros. Isso mantem a
estrutura compativel com a base orientada a documentos prevista no backlog.

MongoDB NAO e exigido nesta etapa.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

STATUS_GERADO = "GERADO"

#: Identificadores aceitos em consultas. Restringir o formato impede que um
#: identificador vindo da URL escape do diretorio de armazenamento
#: (por exemplo "../../etc/passwd").
_ID_VALIDO = re.compile(r"^[A-Za-z0-9._-]{1,120}$")


def agora_utc() -> str:
    """Instante atual em ISO-8601 UTC, formato usado por toda a Esteira."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RegistroDocumento:
    """Metadados de um documento emitido.

    Reune o minimo exigido para rastrear o documento: identificador proprio,
    operacao de origem, momento da emissao, tipo, versao do contrato usada,
    caminho do arquivo, situacao e hash de integridade.
    """

    id_operacao: str
    tipo_documento: str
    versao_schema: str
    caminho_pdf: str
    documento_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    criado_em: str = field(default_factory=agora_utc)
    status: str = STATUS_GERADO
    hash_documento: str | None = None
    tipo_produto: str | None = None
    template: str | None = None
    correlacao: dict[str, Any] = field(default_factory=dict)

    def para_documento(self) -> dict[str, Any]:
        """Forma gravada no repositorio.

        ``_id`` repete ``documento_id`` porque era a chave usada pela versao
        1.0.0 e ha consumidores que a leem; ``documento_id`` e o nome
        definitivo.
        """
        return {
            "_id": self.documento_id,
            "documento_id": self.documento_id,
            "id_operacao": self.id_operacao,
            "criado_em": self.criado_em,
            "tipo_documento": self.tipo_documento,
            "tipo_produto": self.tipo_produto,
            "versao_schema": self.versao_schema,
            "caminho_pdf": self.caminho_pdf,
            "status": self.status,
            "hash_documento": self.hash_documento,
            "template": self.template,
            "correlacao": self.correlacao,
        }


class RepositorioDocumentos(ABC):
    """Contrato de persistencia dos metadados documentais.

    Trocar o armazenamento local por uma base orientada a documentos significa
    implementar esta interface; o fluxo do Processo 6 nao muda.
    """

    @abstractmethod
    def salvar(self, registro: RegistroDocumento) -> str:
        """Grava o registro e devolve o identificador do documento."""

    @abstractmethod
    def buscar(self, documento_id: str) -> dict[str, Any] | None:
        """Devolve o registro gravado, ou ``None`` se nao existir."""


class RepositorioArquivosJson(RepositorioDocumentos):
    """Implementacao em arquivos JSON locais, um arquivo por documento."""

    def __init__(self, diretorio: str):
        self.diretorio = diretorio
        os.makedirs(self.diretorio, exist_ok=True)

    def _caminho(self, documento_id: str) -> str | None:
        if not _ID_VALIDO.match(documento_id):
            return None
        return os.path.join(self.diretorio, f"{documento_id}.json")

    def salvar(self, registro: RegistroDocumento) -> str:
        caminho = self._caminho(registro.documento_id)
        if caminho is None:
            raise ValueError(f"Identificador de documento invalido: {registro.documento_id!r}")
        os.makedirs(self.diretorio, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(registro.para_documento(), arquivo, ensure_ascii=False, indent=2)
        return registro.documento_id

    def buscar(self, documento_id: str) -> dict[str, Any] | None:
        caminho = self._caminho(documento_id)
        if caminho is None or not os.path.exists(caminho):
            return None
        with open(caminho, encoding="utf-8") as arquivo:
            return json.load(arquivo)
