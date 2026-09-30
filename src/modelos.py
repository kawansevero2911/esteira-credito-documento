"""Modelos de RESPOSTA da API.

Estes modelos existem para documentar o Swagger/OpenAPI e padronizar o formato
das respostas. A validacao da ENTRADA continua sendo feita pelo JSON Schema do
contrato canonico (``schemas/v1/``), que e o contrato oficial com os demais
grupos.

Essa separacao e deliberada: se a entrada fosse validada por modelo Pydantic, o
FastAPI responderia 422 em outro formato, e o erro 400 DADOS_INVALIDOS
combinado com os outros grupos deixaria de existir.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Saude(BaseModel):
    status: str = Field(description="Situação do serviço.", examples=["ok"])
    servico: str = Field(description="Nome do serviço.", examples=["estruturacao-documentos"])


class DocumentoResumo(BaseModel):
    """Documento emitido, como aparece na resposta do POST."""

    documento_id: str = Field(
        description="Identificador único do documento gerado.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    id_operacao: str = Field(
        description="Identificador de correlação da operação (correlacao.idOperacao).",
        examples=["OP-2026-000123"],
    )
    tipo_documento: str = Field(description="Tipo do documento emitido.", examples=["PROPOSTA_CREDITO"])
    tipo_produto: str | None = Field(
        default=None,
        description="Produto da operação, quando informado no contrato.",
        examples=["FINANCIAMENTO_IMOVEL"],
    )
    versao_schema: str = Field(
        description="Versão do contrato canônico usada na mensagem.", examples=["1.2.0"]
    )
    caminho_pdf: str = Field(
        description="Caminho do PDF gerado.", examples=["storage/pdfs/OP-2026-000123.pdf"]
    )
    status: str = Field(description="Situação do documento.", examples=["GERADO"])
    hash_documento: str | None = Field(
        default=None,
        description="Hash SHA-256 do PDF, para conferência de integridade.",
        examples=["sha256:9f2c..."],
    )
    template: str | None = Field(
        default=None,
        description="Template usado na emissão do PDF.",
        examples=["proposta_imobiliaria"],
    )


class ReferenciaEvento(BaseModel):
    caminhoPdf: str = Field(description="Caminho do PDF gerado.")
    hashDocumento: str | None = Field(default=None, description="Hash SHA-256 do PDF.")
    correlacao: dict[str, Any] = Field(
        default_factory=dict,
        description="Identificadores de correlação da operação, repassados ao consumidor.",
    )


class EventoDocumentoGerado(BaseModel):
    """Evento `documento.gerado`, em formato versionado.

    Os campos em snake_case no final repetem informações já presentes acima e
    existem apenas por compatibilidade com os consumidores da versão 1.0.0.
    """

    eventType: str = Field(description="Tipo do evento.", examples=["documento.gerado"])
    eventVersion: str = Field(description="Versão do formato do evento.", examples=["1.0"])
    eventId: str = Field(description="Identificador único desta publicação.")
    occurredAt: str = Field(
        description="Momento da publicação (ISO-8601 UTC).",
        examples=["2026-09-25T23:10:00.000000+00:00"],
    )
    idOperacao: str = Field(description="Identificador de correlação da operação.")
    documentoId: str = Field(description="Identificador do documento gerado.")
    tipoDocumento: str = Field(description="Tipo do documento gerado.")
    schemaVersion: str = Field(description="Versão do contrato canônico usada.")
    referencia: ReferenciaEvento

    evento: str = Field(description="Compatibilidade v1.0.0: mesmo valor de eventType.")
    documento_id: str = Field(description="Compatibilidade v1.0.0: mesmo valor de documentoId.")
    id_operacao: str = Field(description="Compatibilidade v1.0.0: mesmo valor de idOperacao.")
    caminho_pdf: str = Field(description="Compatibilidade v1.0.0: caminho do PDF.")
    publicado_em: str = Field(description="Compatibilidade v1.0.0: mesmo valor de occurredAt.")


class DocumentoCriado(BaseModel):
    status: str = Field(description="Resultado do processamento.", examples=["sucesso"])
    documento_id: str = Field(
        description="Identificador único do documento gerado.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    formatoEntrada: str = Field(
        description=(
            "Formato em que a mensagem chegou: `canonico` para o contrato 1.2.0 "
            "ou `legado_v1` para o formato plano da versão 1.0.0, que é convertido "
            "antes da validação."
        ),
        examples=["canonico"],
    )
    documento: DocumentoResumo
    evento: EventoDocumentoGerado


class DocumentoMetadados(BaseModel):
    """Registro gravado no repositório de metadados documentais."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(
        alias="_id",
        description="Identificador único do documento. Repete `documento_id`; mantido desde a v1.0.0.",
        examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
    )
    documento_id: str = Field(description="Identificador único do documento.")
    id_operacao: str = Field(description="Identificador de correlação da operação.")
    criado_em: str = Field(
        description="Data e hora de criação (ISO-8601 UTC).",
        examples=["2026-09-25T23:10:00.000000+00:00"],
    )
    tipo_documento: str = Field(description="Tipo do documento emitido.")
    tipo_produto: str | None = Field(default=None, description="Produto da operação, quando informado.")
    versao_schema: str = Field(description="Versão do contrato canônico usada.")
    caminho_pdf: str = Field(description="Caminho do PDF gerado.")
    status: str = Field(description="Situação do documento.", examples=["GERADO"])
    hash_documento: str | None = Field(default=None, description="Hash SHA-256 do PDF.")
    template: str | None = Field(default=None, description="Template usado na emissão.")
    correlacao: dict[str, Any] = Field(
        default_factory=dict, description="Identificadores de correlação da operação."
    )


class OcorrenciaValidacao(BaseModel):
    campo: str = Field(description="Caminho do campo com problema.", examples=["cliente.dadosPF.cpf"])
    mensagem: str = Field(description="Descrição do problema encontrado.")
    regra: str | None = Field(
        default=None,
        description="Palavra-chave do JSON Schema que reprovou o valor.",
        examples=["pattern"],
    )


class ErroDadosInvalidos(BaseModel):
    status: str = Field(examples=["erro"])
    codigo: str = Field(description="Código do erro.", examples=["DADOS_INVALIDOS"])
    mensagem: str = Field(examples=["Os dados recebidos não atendem ao contrato JSON Schema."])
    detalhes: list[str] = Field(
        description="Falhas encontradas, no formato `campo: motivo`. Formato mantido desde a v1.0.0.",
        examples=[[
            "cliente.dadosPF.cpf: '123.456.789-01' does not match '^[0-9]{11}$'",
            "financiamento.imobiliario.prazoMeses: 0 is less than the minimum of 1",
        ]],
    )
    erros: list[OcorrenciaValidacao] = Field(
        description="As mesmas falhas em forma estruturada, mais simples de tratar em outra linguagem."
    )
    formatoEntrada: str = Field(
        description="Formato em que a mensagem chegou (`canonico` ou `legado_v1`).",
        examples=["canonico"],
    )
    versaoContrato: str = Field(
        description="Versão do contrato canônico contra a qual a mensagem foi validada.",
        examples=["1.2.0"],
    )


class ErroNaoEncontrado(BaseModel):
    detail: str = Field(examples=["Documento não encontrado."])
