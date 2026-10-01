from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, RedirectResponse

from .contrato import componentes_openapi, versao_contrato
from .modelos import (
    DocumentoCriado,
    DocumentoMetadados,
    ErroDadosInvalidos,
    ErroNaoEncontrado,
    Saude,
)
from .processo import BASE_DIR, buscar_documento, executar_processo

EXEMPLOS_DIR = BASE_DIR / "examples"

NOME_COMPONENTE_CONTRATO = "OperacaoCredito"

DESCRICAO_API = f"""
API do **Processo 6 — Estruturação de Documentos Não Relacionais (JSON, PDF)**
da Esteira de Crédito.

Recebe uma operação de crédito em JSON, valida contra o **contrato canônico da
Esteira** (JSON Schema Draft 2020-12, versão **{versao_contrato()}**), mapeia os
dados para o modelo documental, gera o PDF, armazena os metadados e publica o
evento `documento.gerado`.

### Fluxo
`receber → validar → (dados válidos?) → mapear → gerar PDF → armazenar → publicar evento`

Se a validação falhar, o fluxo para: **nenhum PDF é gerado** e nenhum registro
documental é criado.

### Contrato único, blocos por processo
O corpo do `POST /api/documentos` é o contrato canônico `{NOME_COMPONENTE_CONTRATO}`.
Ele é dividido em blocos, e **cada processo preenche apenas o seu**:

| Bloco | Processo responsável |
|---|---|
| `correlacao`, `metadados` | comuns a todos |
| `documento` | 6 — Estruturação de Documentos |
| `cliente`, `cadastro`, `credito` | 3 — Crédito PF e PJ |
| `promocao` | 1 — Promoções e Ações de Crédito |
| `produtoFinanceiro` | 7 — Produtos Financeiros |
| `financiamento` | 4 — Imóveis / 8 — Automotivo |
| `score` | 10 — Score |
| `juros` | 5 — Cálculo de Juros |
| `decisao` | 9 — Decisão |
| `operacaoFinanceira` | 2 — Controle Financeiro de Operações |

Só `schemaVersion`, `correlacao`, `documento` e `cliente` são obrigatórios
sempre. O restante depende do produto — as regras condicionais estão no schema
(`allOf` / `if` / `then`).

A linguagem de quem integra não importa: a comunicação é HTTP + JSON + JSON Schema.

### Como testar por aqui
1. Abra `POST /api/documentos` e clique em **Try it out**.
2. Escolha um exemplo na lista (`operacao_valida`, `operacao_completa`,
   `operacao_invalida`…).
3. Clique em **Execute** e copie o `documento_id` da resposta.
4. Use o `documento_id` em `GET /api/documentos/{{documento_id}}`.
"""

TAGS = [
    {
        "name": "Infraestrutura",
        "description": "Verificação de disponibilidade do serviço.",
    },
    {
        "name": "Documentos",
        "description": (
            "Estruturação, emissão e consulta de documentos da operação de crédito. "
            "A entrada segue o contrato canônico da Esteira."
        ),
    },
]


def _carregar_exemplo(nome: str) -> dict:
    with open(EXEMPLOS_DIR / nome, encoding="utf-8") as arquivo:
        return json.load(arquivo)


EXEMPLOS_OPERACAO = {
    "operacao_valida": {
        "summary": "1. Financiamento imobiliário PF",
        "description": (
            "Operação enviada pelo processo Financiamento de Imóveis, sem score, "
            "decisão nem operação financeira. Resultado esperado: HTTP 201."
        ),
        "value": _carregar_exemplo("operacao_valida.json"),
    },
    "operacao_com_score": {
        "summary": "2. Com score",
        "description": (
            "Mesma estrutura, acrescida do bloco `score` preenchido pelo processo "
            "Score. Resultado esperado: HTTP 201."
        ),
        "value": _carregar_exemplo("operacao_com_score.json"),
    },
    "operacao_com_decisao": {
        "summary": "3. Com decisão e juros",
        "description": (
            "Acrescenta os blocos `juros` e `decisao`. Resultado esperado: HTTP 201."
        ),
        "value": _carregar_exemplo("operacao_com_decisao.json"),
    },
    "operacao_completa": {
        "summary": "4. Com operação financeira e cronograma",
        "description": (
            "Operação percorrendo a Esteira inteira, com o bloco "
            "`operacaoFinanceira` e o cronograma de parcelas do processo Controle "
            "Financeiro. Resultado esperado: HTTP 201."
        ),
        "value": _carregar_exemplo("operacao_completa.json"),
    },
    "operacao_credito_pj": {
        "summary": "5. Crédito pessoa jurídica",
        "description": (
            "Mostra que o contrato não é exclusivo de pessoa física. O bloco "
            "`dadosPJ` não exige campos porque o contrato de PJ ainda depende do "
            "grupo Crédito PF e PJ. Resultado esperado: HTTP 201."
        ),
        "value": _carregar_exemplo("operacao_credito_pj.json"),
    },
    "legado_v1_plano": {
        "summary": "6. Formato plano da v1.0.0 (compatibilidade)",
        "description": (
            "Formato antigo, em snake_case. É convertido para o contrato canônico "
            "antes da validação. Resultado esperado: HTTP 201 com "
            "`formatoEntrada: legado_v1`."
        ),
        "value": _carregar_exemplo("legado_v1_plano.json"),
    },
    "operacao_invalida": {
        "summary": "7. Operação inválida",
        "description": (
            "CPF com pontuação, data inexistente, valor negativo, prazo zero, "
            "enums inválidos, score fora de 0–1000 e campo obrigatório ausente. "
            "Resultado esperado: HTTP 400 com código DADOS_INVALIDOS e nenhum PDF gerado."
        ),
        "value": _carregar_exemplo("operacao_invalida.json"),
    },
}

app = FastAPI(
    title="Esteira de Crédito — Estruturação de Documentos",
    description=DESCRICAO_API,
    version="1.2.0",
    openapi_tags=TAGS,
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "displayRequestDuration": True,
    },
)

# O banco de provas de web/index.html e as paginas dos outros grupos rodam em
# outra origem (ou em file://, cuja origem o navegador envia como "null"), e o
# navegador bloqueia a chamada sem estes cabecalhos.
#
# ATENCAO: liberar qualquer origem e adequado a um servico de teste rodando em
# localhost, que e o caso deste projeto na disciplina. Antes de expor o servico
# em rede, troque allow_origins pela lista das origens que devem ter acesso.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/", include_in_schema=False)
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")


@app.get(
    "/api/saude",
    tags=["Infraestrutura"],
    summary="Verificar disponibilidade",
    description=(
        "Retorna `ok` quando o serviço está no ar. Pode ser usado pelos demais "
        "grupos antes de integrar."
    ),
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
        "Valida a operação contra o contrato canônico `OperacaoCredito`. Se for "
        "válida, mapeia para o modelo documental, gera o PDF, armazena os "
        "metadados e publica o evento `documento.gerado`. Se for inválida, o "
        "fluxo é interrompido: nenhum PDF é gerado e nenhum registro é criado.\n\n"
        "Aceita também o formato plano da versão 1.0.0, que é convertido para o "
        "contrato canônico antes da validação — a resposta indica qual formato "
        "foi recebido em `formatoEntrada`."
    ),
    response_model=DocumentoCriado,
    response_description="Documento gerado com sucesso.",
    responses={
        400: {
            "model": ErroDadosInvalidos,
            "description": (
                "Os dados não atendem ao contrato JSON Schema. Nenhum documento foi gerado."
            ),
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


def openapi_personalizado() -> dict:
    """OpenAPI gerado da própria API, com o contrato publicado por bloco.

    O corpo do POST é documentado com o MESMO contrato usado na validação, para
    que Swagger e validação nunca fiquem diferentes. Cada bloco do contrato vira
    um componente com nome próprio (`Cliente`, `Score`, `Decisao`…), de modo que
    quem integra consiga abrir bloco por bloco no Swagger.
    """
    if app.openapi_schema:
        return app.openapi_schema

    especificacao = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    componentes = especificacao.setdefault("components", {}).setdefault("schemas", {})
    componentes.update(componentes_openapi())

    conteudo = especificacao["paths"]["/api/documentos"]["post"]["requestBody"]["content"][
        "application/json"
    ]
    conteudo["schema"] = {"$ref": f"#/components/schemas/{NOME_COMPONENTE_CONTRATO}"}

    app.openapi_schema = especificacao
    return app.openapi_schema


app.openapi = openapi_personalizado
