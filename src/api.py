from __future__ import annotations

import copy
import json
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException, Path
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse

from .modelos import (
    DocumentoCriado,
    DocumentoMetadados,
    ErroDadosInvalidos,
    ErroNaoEncontrado,
    Saude,
)
from .processo import BASE_DIR, SCHEMA_PATH, buscar_documento, executar_processo

EXAMPLES_DIR = BASE_DIR / "examples"

DESCRICAO_API = """
API do grupo **Estruturação de Documentos Não Relacionais (JSON, PDF)** da
Esteira de Crédito.

Recebe uma operação de crédito em JSON, valida contra o contrato
(JSON Schema Draft 2020-12), mapeia os dados para o modelo documental, gera o
PDF, armazena os metadados e publica o evento `documento.gerado`.

### Fluxo
`receber → validar → (dados válidos?) → mapear → gerar PDF → armazenar → publicar evento`

### Como testar por aqui
1. Abra `POST /api/documentos` e clique em **Try it out**.
2. Escolha o exemplo **operacao_valida** (ou **operacao_invalida** para ver o erro 400).
3. Clique em **Execute** e copie o `documento_id` da resposta.
4. Use o `documento_id` em `GET /api/documentos/{documento_id}`.
"""

TAGS = [
    {
        "name": "Infraestrutura",
        "description": "Verificação de disponibilidade do serviço.",
    },
    {
        "name": "Documentos",
        "description": "Estruturação, emissão e consulta de documentos da operação de crédito.",
    },
]


def _carregar_exemplo(nome: str) -> dict:
    with open(EXAMPLES_DIR / nome, encoding="utf-8") as arquivo:
        return json.load(arquivo)


EXEMPLOS_OPERACAO = {
    "operacao_valida": {
        "summary": "Operação válida (financiamento de automóvel)",
        "description": "Atende ao contrato. Resultado esperado: HTTP 201.",
        "value": _carregar_exemplo("operacao_valida.json"),
    },
    "operacao_invalida": {
        "summary": "Operação inválida",
        "description": (
            "Sem cliente.documento, valor negativo e prazo zero. "
            "Resultado esperado: HTTP 400 com código DADOS_INVALIDOS."
        ),
        "value": _carregar_exemplo("operacao_invalida.json"),
    },
}

app = FastAPI(
    title="Esteira de Crédito — Estruturação de Documentos",
    description=DESCRICAO_API,
    version="1.1.0",
    openapi_tags=TAGS,
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 1,
        "displayRequestDuration": True,
    },
)


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get(
    "/api/saude",
    tags=["Infraestrutura"],
    summary="Verificar disponibilidade",
    description="Retorna `ok` quando o serviço está no ar. Pode ser usado pelos demais grupos antes de integrar.",
    response_model=Saude,
)
def saude() -> dict:
    return {"status": "ok", "servico": "estruturacao-documentos"}


@app.post(
    "/api/documentos",
    status_code=201,
    tags=["Documentos"],
    summary="Gerar documento de uma operação de crédito",
    description=(
        "Valida a operação contra o JSON Schema `OperacaoCredito`. Se for válida, "
        "gera o PDF, armazena os metadados e publica o evento `documento.gerado`. "
        "Se for inválida, o fluxo é interrompido e nenhum PDF é gerado."
    ),
    response_model=DocumentoCriado,
    response_description="Documento gerado com sucesso.",
    responses={
        400: {
            "model": ErroDadosInvalidos,
            "description": "Os dados não atendem ao contrato JSON Schema. Nenhum documento foi gerado.",
        },
    },
)
def criar_documento(
    operacao: Annotated[dict[str, Any], Body(openapi_examples=EXEMPLOS_OPERACAO)],
):
    resultado = executar_processo(operacao)
    if resultado["status"] == "erro":
        return JSONResponse(status_code=400, content=resultado)
    return resultado


@app.get(
    "/api/documentos/{documento_id}",
    tags=["Documentos"],
    summary="Consultar metadados de um documento",
    description="Retorna os metadados armazenados de um documento gerado anteriormente.",
    response_model=DocumentoMetadados,
    responses={404: {"model": ErroNaoEncontrado, "description": "Documento não encontrado."}},
)
def obter_documento(
    documento_id: Annotated[
        str,
        Path(
            description="Identificador retornado em `documento_id` pelo `POST /api/documentos`.",
            examples=["3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42"],
        ),
    ],
) -> dict:
    documento = buscar_documento(documento_id)
    if documento is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return documento


def _schema_operacao_para_openapi() -> dict:
    """Converte o JSON Schema do contrato em um componente do OpenAPI.

    O OpenAPI 3.1 usa JSON Schema 2020-12, então o arquivo do contrato pode ser
    reaproveitado diretamente. Só removemos $schema e $id, que não fazem
    sentido dentro de components/schemas.
    """
    with open(SCHEMA_PATH, encoding="utf-8") as arquivo:
        schema = json.load(arquivo)
    schema = copy.deepcopy(schema)
    schema.pop("$schema", None)
    schema.pop("$id", None)
    schema.setdefault(
        "description",
        "Contrato de entrada da operação de crédito (arquivo schemas/operacao_credito.schema.json).",
    )
    return schema


def openapi_personalizado() -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    especificacao = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    # O corpo do POST é documentado com o MESMO JSON Schema usado na validação,
    # para que Swagger e validação nunca fiquem diferentes.
    componentes = especificacao.setdefault("components", {}).setdefault("schemas", {})
    componentes["OperacaoCredito"] = _schema_operacao_para_openapi()
    conteudo = especificacao["paths"]["/api/documentos"]["post"]["requestBody"]["content"]["application/json"]
    conteudo["schema"] = {"$ref": "#/components/schemas/OperacaoCredito"}

    app.openapi_schema = especificacao
    return app.openapi_schema


app.openapi = openapi_personalizado
