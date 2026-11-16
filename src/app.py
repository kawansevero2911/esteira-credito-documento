"""API REST da camada de Estruturação e Emissão de Documentos (Esteira de Crédito)."""
from __future__ import annotations
import json
import os
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from .modelos import (DocumentoCriado, DocumentoMetadados, DocumentoIntegradoCriado, ErroIntegracao, ErroValidacaoResposta,
                      NaoEncontrado, Saude)
from .processo import ProcessoEmissaoDocumento
from .publicador_evento import PublicadorArquivo
from .repositorio import RepositorioArquivo, RepositorioMongoDB
from .validador import ErroValidacao
from .integracao_finops import FinOpsErro, consultar_finops, emitir_finops
from .integracao_credcasa import CredCasaErro, consultar_credcasa, emitir_credcasa
from .integracao_juros import JurosErro, emitir_juros

VERSAO = "1.4.0"
BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schemas" / "v1" / "operacao_credito.schema.json"
EXEMPLOS_DIR = BASE_DIR / "exemplos"

DESCRICAO = """
Camada de **estruturação e emissão de documentos** da Esteira de Crédito.

Recebe os dados de uma operação (JSON), valida contra o **JSON Schema** (o contrato entre
os módulos), gera o documento em **PDF**, armazena os metadados em base orientada a
documentos e publica o evento `documento.gerado`.
"""

TAGS = [
    {"name": "Documentos", "description": "Emissão e consulta de documentos de operações de crédito."},
    {"name": "Contrato", "description": "JSON Schema que os demais módulos devem respeitar."},
    {"name": "Operação", "description": "Verificação de saúde do serviço."},
]


def _ler_json(caminho: Path) -> dict:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def create_app(storage_dir: str | Path | None = None, imprimir_eventos: bool = True) -> FastAPI:
    storage = Path(storage_dir or os.environ.get("STORAGE_DIR", BASE_DIR / "storage"))
    schema = _ler_json(SCHEMA_PATH)

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    repositorio_documentos = (RepositorioMongoDB(mongo_uri, os.getenv("MONGODB_DB", "esteira_credito"))
                               if mongo_uri else RepositorioArquivo(storage))
    processo = ProcessoEmissaoDocumento(
        schema=schema,
        repositorio=repositorio_documentos,
        publicador=PublicadorArquivo(storage, imprimir=imprimir_eventos),
        diretorio_base=storage,
    )
    repositorio = processo.repositorio
    schema_finops = _ler_json(BASE_DIR / "schemas" / "v1" / "finops_consulta.schema.json")

    schema_credcasa = _ler_json(BASE_DIR / "schemas" / "v1" / "credcasa_proposta.schema.json")

    schema_juros = _ler_json(BASE_DIR / "schemas" / "v1" / "juros_operacao.schema.json")

    app = FastAPI(title="Esteira de Crédito — Estruturação de Documentos",
                  description=DESCRICAO, version=VERSAO, openapi_tags=TAGS)

    exemplos = {
        "valida": {"summary": "Operação válida (financiamento de automóvel)",
                   "value": _ler_json(EXEMPLOS_DIR / "operacao_valida.json")},
        "invalida": {"summary": "Operação inválida (produto, valor e prazo fora do contrato)",
                     "value": _ler_json(EXEMPLOS_DIR / "operacao_invalida.json")},
    }

    @app.get("/", include_in_schema=False)
    def raiz():
        return RedirectResponse("/docs")

    @app.get("/api/saude", response_model=Saude, tags=["Operação"],
             summary="Verificar saúde do serviço")
    def saude():
        return {"status": "ok", "servico": "estruturacao-de-documentos", "versao": VERSAO}

    @app.get("/api/schemas/operacao-credito", tags=["Contrato"],
             summary="Obter o JSON Schema do contrato OperacaoCredito",
             description="Os módulos consumidores podem baixar o contrato vigente por aqui.")
    def obter_schema():
        return schema

    @app.post("/api/documentos", status_code=201, response_model=DocumentoCriado, tags=["Documentos"],
              summary="Receber operação e emitir documento",
              description="Valida a operação contra o contrato `OperacaoCredito`. Se válida, gera o PDF, "
                          "armazena os metadados e publica o evento `documento.gerado`. "
                          "Se inválida, **nada é gerado** e a resposta lista os erros.",
              responses={400: {"model": ErroValidacaoResposta,
                               "description": "DADOS_INVALIDOS: a operação não respeita o contrato."}})
    def criar_documento(operacao: dict = Body(..., openapi_examples=exemplos)):
        try:
            return processo.executar(operacao)
        except ErroValidacao as e:
            return JSONResponse(status_code=400, content={
                "codigo": "DADOS_INVALIDOS",
                "mensagem": "A operação não respeita o contrato OperacaoCredito.",
                "erros": e.erros,
            })

    @app.post("/api/documentos/finops", status_code=201, response_model=DocumentoIntegradoCriado, tags=["Documentos"],
              responses={400: {"model": ErroIntegracao, "description": "JSON inválido"}},
              summary="Gerar demonstrativo a partir de JSONs do FinOps (sem conexão externa)")
    def criar_finops_json(dados: dict = Body(..., examples=[_ler_json(EXEMPLOS_DIR / "finops_consulta_exemplo.json")])):
        try:
            return emitir_finops(dados.get("operacao"), dados.get("parcelas"), schema_finops,
                                 storage, repositorio, processo.publicador)
        except (FinOpsErro, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/documentos/finops/{identificador}/consultar", status_code=201,
              tags=["Documentos"], response_model=DocumentoIntegradoCriado,
              responses={400: {"model": ErroIntegracao}, 502: {"model": ErroIntegracao, "description": "Falha no FinOps"}},
              summary="Consultar FinOps via GET e gerar demonstrativo")
    def criar_finops_consulta(identificador: str):
        try:
            operacao, parcelas = consultar_finops(identificador)
            return emitir_finops(operacao, parcelas, schema_finops, storage, repositorio, processo.publicador)
        except FinOpsErro as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/schemas/credcasa", tags=["Contrato"], summary="Contrato mínimo da proposta CredCasa")
    def obter_schema_credcasa():
        return schema_credcasa

    @app.post("/api/documentos/credcasa", status_code=201, tags=["Documentos"], response_model=DocumentoIntegradoCriado,
              responses={400: {"model": ErroIntegracao, "description": "JSON inválido"}},
              summary="Gerar proposta imobiliária com JSON local (sem CredCasa online)")
    def criar_credcasa_json(dados: dict = Body(..., examples=[_ler_json(EXEMPLOS_DIR / "credcasa_proposta_exemplo.json")])):
        try:
            return emitir_credcasa(dados, schema_credcasa, storage, repositorio, processo.publicador)
        except CredCasaErro as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/documentos/credcasa/{identificador}/consultar", status_code=201,
              tags=["Documentos"], response_model=DocumentoIntegradoCriado,
              responses={400: {"model": ErroIntegracao}, 502: {"model": ErroIntegracao, "description": "Falha no CredCasa"}},
              summary="Consultar CredCasa via GET e emitir proposta PDF")
    def criar_credcasa_consulta(identificador: str):
        try:
            dados = consultar_credcasa(identificador)
            return emitir_credcasa(dados, schema_credcasa, storage, repositorio, processo.publicador)
        except CredCasaErro as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/schemas/juros", tags=["Contrato"], summary="Contrato JSON do grupo Juros")
    def obter_schema_juros():
        return schema_juros

    @app.post("/api/documentos/juros", status_code=201, tags=["Documentos"],
              response_model=DocumentoIntegradoCriado,
              responses={400: {"model": ErroIntegracao, "description": "JSON de Juros inválido"}},
              summary="Receber JSON de Juros localmente, sem API pública",
              description="O grupo Juros pode entregar um arquivo JSON; use o importador offline, "
                          "ou faça POST para localhost no mesmo computador. Não exige internet nem túnel.")
    def criar_juros_json(dados: dict = Body(...)):
        try:
            return emitir_juros(dados, schema_juros, storage, repositorio, processo.publicador)
        except JurosErro as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/documentos/{documento_id}", response_model=DocumentoMetadados,
             response_model_by_alias=True, tags=["Documentos"],
             summary="Consultar metadados de um documento",
             responses={404: {"model": NaoEncontrado, "description": "Documento não encontrado."}})
    def consultar_documento(documento_id: str):
        registro = repositorio.buscar(documento_id)
        if registro is None:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        return registro

    @app.get("/api/documentos/{documento_id}/pdf", tags=["Documentos"],
             summary="Baixar o PDF do documento",
             responses={200: {"content": {"application/pdf": {}}},
                        404: {"model": NaoEncontrado, "description": "Documento não encontrado."}})
    def baixar_pdf(documento_id: str):
        registro = repositorio.buscar(documento_id)
        if registro is None:
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        caminho = storage / registro["caminho_pdf"]
        if not caminho.exists():
            raise HTTPException(status_code=404, detail="Documento não encontrado")
        return FileResponse(caminho, media_type="application/pdf", filename=f"{documento_id}.pdf")

    return app


app = create_app()
