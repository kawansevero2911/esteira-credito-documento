"""Modelos de resposta da API (alimentam a documentação Swagger/OpenAPI)."""
from __future__ import annotations
from pydantic import BaseModel, Field


class Saude(BaseModel):
    status: str = Field(examples=["ok"])
    servico: str
    versao: str


class ResumoOperacao(BaseModel):
    id_operacao: str
    tipo_produto: str
    cliente: str
    valor: float


class EventoDocumentoGerado(BaseModel):
    evento: str = Field(examples=["documento.gerado"])
    id_operacao: str
    documento_id: str
    caminho_pdf: str
    publicado_em: str


class DocumentoCriado(BaseModel):
    documento_id: str
    resumo: ResumoOperacao
    evento: EventoDocumentoGerado


class ErroCampo(BaseModel):
    campo: str = Field(examples=["valor"])
    mensagem: str


class ErroValidacaoResposta(BaseModel):
    codigo: str = Field(examples=["DADOS_INVALIDOS"])
    mensagem: str
    erros: list[ErroCampo]


class DocumentoMetadados(BaseModel):
    id: str = Field(alias="_id")
    criado_em: str
    id_operacao: str
    tipo_produto: str
    caminho_pdf: str
    tipo_documento: str | None = None
    origem: str | None = None
    quantidade_parcelas: int | None = None
    versao_schema: str | None = None

    model_config = {"populate_by_name": True}


class NaoEncontrado(BaseModel):
    detail: str = Field(examples=["Documento não encontrado"])


class DocumentoIntegradoCriado(BaseModel):
    documento_id: str
    id_operacao: str
    tipo_documento: str
    quantidade_parcelas: int | None = None
    url_pdf: str | None = None
    evento: EventoDocumentoGerado


class ErroIntegracao(BaseModel):
    detail: str
