"""Publicacao do evento ``documento.gerado``.

O evento continua sendo gravado localmente, em arquivo JSON - nao ha Kafka nem
RabbitMQ nesta etapa, e nao deve haver. O que mudou:

* o evento ganhou estrutura versionada (``eventType``, ``eventVersion``,
  ``eventId``, ``occurredAt``, ``referencia``), para que um consumidor saiba
  interpretar o formato que recebeu;
* a publicacao virou uma INTERFACE (``PublicadorEventos``). Substituir o arquivo
  por um barramento real e implementar a interface, sem mexer no fluxo.

O campo ``evento`` repete ``eventType`` por compatibilidade com os consumidores
da versao 1.0.0.
"""
from __future__ import annotations

import json
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .repositorio import agora_utc

TIPO_EVENTO_DOCUMENTO_GERADO = "documento.gerado"
VERSAO_EVENTO = "1.0"


@dataclass
class EventoDocumento:
    """Evento de documento emitido, em formato versionado."""

    documento_id: str
    id_operacao: str
    tipo_documento: str
    versao_schema: str
    caminho_pdf: str
    hash_documento: str | None = None
    correlacao: dict[str, Any] = field(default_factory=dict)
    tipo_evento: str = TIPO_EVENTO_DOCUMENTO_GERADO
    versao_evento: str = VERSAO_EVENTO
    evento_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ocorrido_em: str = field(default_factory=agora_utc)

    def para_mensagem(self) -> dict[str, Any]:
        return {
            "eventType": self.tipo_evento,
            "eventVersion": self.versao_evento,
            "eventId": self.evento_id,
            "occurredAt": self.ocorrido_em,
            "idOperacao": self.id_operacao,
            "documentoId": self.documento_id,
            "tipoDocumento": self.tipo_documento,
            "schemaVersion": self.versao_schema,
            "referencia": {
                "caminhoPdf": self.caminho_pdf,
                "hashDocumento": self.hash_documento,
                "correlacao": self.correlacao,
            },
            # Campos da versao 1.0.0, mantidos para nao quebrar consumidores.
            "evento": self.tipo_evento,
            "documento_id": self.documento_id,
            "id_operacao": self.id_operacao,
            "caminho_pdf": self.caminho_pdf,
            "publicado_em": self.ocorrido_em,
        }


class PublicadorEventos(ABC):
    """Contrato de publicacao de eventos do Processo 6."""

    @abstractmethod
    def publicar(self, evento: EventoDocumento) -> dict[str, Any]:
        """Publica o evento e devolve a mensagem publicada."""


class PublicadorArquivoJson(PublicadorEventos):
    """Publicacao simulada: grava a mensagem em arquivo, um por evento.

    Substituivel por um barramento real sem alterar o fluxo do processo.
    """

    def __init__(self, diretorio: str):
        self.diretorio = diretorio

    def publicar(self, evento: EventoDocumento) -> dict[str, Any]:
        mensagem = evento.para_mensagem()
        os.makedirs(self.diretorio, exist_ok=True)
        caminho = os.path.join(self.diretorio, f"{evento.documento_id}.json")
        with open(caminho, "w", encoding="utf-8") as arquivo:
            json.dump(mensagem, arquivo, ensure_ascii=False, indent=2)
        return mensagem
