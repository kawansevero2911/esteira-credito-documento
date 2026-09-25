"""Modelos de resposta da API.

Estes modelos existem para documentar (no Swagger/OpenAPI) e padronizar o
formato das respostas. A validação da ENTRADA continua sendo feita pelo
JSON Schema em schemas/operacao_credito.schema.json, que é o contrato oficial
com os demais grupos.
"""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Saude(BaseModel):
    status: str = Field(description="Situação do serviço.", examples=["ok"])
    servico: str = Field(description="Nome do serviço.", examples=["estruturacao-documentos"])


class DocumentoResumo(BaseModel):
    id_operacao: str = Field(description="Identificador da operação de crédito.", examples=["OP-2026-000123"])
    tipo_produto: str = Field(description="Tipo do produto financeiro.", examples=["financiamento_automovel"])
    caminho_pdf: str = Field(description="Caminho do PDF gerado.", examples=["storage/pdfs/OP-2026-000123.pdf"])


class EventoDocumentoGerado(BaseModel):
    evento: str = Field(description="Nome do evento publicado.", examples=["documento.gerado"])
    id_operacao: str = Field(description="Identificador da operação de crédito.", examples=["OP-2026-000123"])
    documento_id: str = Field(
        description="Identificador do documento gerado.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    caminho_pdf: str = Field(description="Caminho do PDF gerado.", examples=["storage/pdfs/OP-2026-000123.pdf"])
    publicado_em: str = Field(
        description="Data e hora da publicação (ISO 8601, UTC).",
        examples=["2026-09-25T23:10:00.000000+00:00"],
    )


class DocumentoCriado(BaseModel):
    status: str = Field(description="Resultado do processamento.", examples=["sucesso"])
    documento_id: str = Field(
        description="Identificador único do documento gerado.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    documento: DocumentoResumo
    evento: EventoDocumentoGerado


class DocumentoMetadados(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        alias="_id",
        description="Identificador único do documento.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    criado_em: str = Field(
        description="Data e hora de criação (ISO 8601, UTC).",
        examples=["2026-09-25T23:10:00.000000+00:00"],
    )
    id_operacao: str = Field(description="Identificador da operação de crédito.", examples=["OP-2026-000123"])
    tipo_produto: str = Field(description="Tipo do produto financeiro.", examples=["financiamento_automovel"])
    caminho_pdf: str = Field(description="Caminho do PDF gerado.", examples=["storage/pdfs/OP-2026-000123.pdf"])


class ErroDadosInvalidos(BaseModel):
    status: str = Field(examples=["erro"])
    codigo: str = Field(description="Código do erro.", examples=["DADOS_INVALIDOS"])
    mensagem: str = Field(examples=["Os dados recebidos não atendem ao contrato JSON Schema."])
    detalhes: list[str] = Field(
        description="Lista das falhas encontradas na validação, no formato campo: motivo.",
        examples=[[
            "cliente: 'documento' is a required property",
            "prazo_meses: 0 is less than the minimum of 1",
            "valor: -1000 is less than the minimum of 0",
        ]],
    )


class ErroNaoEncontrado(BaseModel):
    detail: str = Field(examples=["Documento não encontrado."])
