"""Testes da camada HTTP: endpoints, respostas e documentacao Swagger/OpenAPI."""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import EXEMPLOS_OPERACAO, app
from src.contrato import componentes_openapi, versao_contrato
from tests.apoio import exemplo

client = TestClient(app)

CAMINHOS = {
    "/api/saude",
    "/api/documentos",
    "/api/documentos/{documento_id}",
}


# ---------------------------------------------------------------- endpoints

def test_saude():
    resposta = client.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok", "servico": "estruturacao-documentos"}


def test_criar_documento_valido(storage_temporario):
    resposta = client.post("/api/documentos", json=exemplo("operacao_valida"))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "sucesso"
    assert corpo["documento_id"]
    assert corpo["formatoEntrada"] == "canonico"
    assert corpo["evento"]["evento"] == "documento.gerado"
    assert corpo["evento"]["eventType"] == "documento.gerado"
    assert corpo["documento"]["versao_schema"] == versao_contrato()
    assert (storage_temporario / "pdfs" / "OP-2026-000123.pdf").exists()


def test_criar_documento_de_cada_exemplo_valido(storage_temporario):
    for nome in (
        "operacao_com_score",
        "operacao_com_decisao",
        "operacao_completa",
        "operacao_credito_pj",
    ):
        resposta = client.post("/api/documentos", json=exemplo(nome))
        assert resposta.status_code == 201, (nome, resposta.json())


def test_criar_documento_no_formato_legado(storage_temporario):
    """Quem integrava com o contrato v1.0.0 continua funcionando."""
    resposta = client.post("/api/documentos", json=exemplo("legado_v1_plano"))
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["formatoEntrada"] == "legado_v1"
    assert corpo["documento"]["id_operacao"] == "OP-2026-000999"


def test_rejeitar_documento_invalido(storage_temporario):
    resposta = client.post("/api/documentos", json=exemplo("operacao_invalida"))
    assert resposta.status_code == 400
    corpo = resposta.json()
    assert corpo["codigo"] == "DADOS_INVALIDOS"
    assert corpo["detalhes"]
    assert corpo["erros"][0]["campo"]
    assert corpo["versaoContrato"] == versao_contrato()
    assert not (storage_temporario / "pdfs").exists()


def test_corpo_que_nao_e_objeto_json(storage_temporario):
    """O FastAPI trata o formato do corpo; o 400 fica para o contrato."""
    resposta = client.post("/api/documentos", json=["nao", "e", "objeto"])
    assert resposta.status_code in (400, 422)
    assert not (storage_temporario / "pdfs").exists()


def test_consultar_documento_criado(storage_temporario):
    criado = client.post("/api/documentos", json=exemplo("operacao_valida")).json()
    resposta = client.get(f"/api/documentos/{criado['documento_id']}")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["_id"] == criado["documento_id"]
    assert corpo["documento_id"] == criado["documento_id"]
    assert corpo["id_operacao"] == "OP-2026-000123"
    assert corpo["criado_em"]
    assert corpo["status"] == "GERADO"
    assert corpo["hash_documento"].startswith("sha256:")


def test_consultar_documento_inexistente(storage_temporario):
    resposta = client.get("/api/documentos/nao-existe")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Documento não encontrado."}


# ---------------------------------------------------------- Swagger / OpenAPI

def test_swagger_ui_disponivel():
    resposta = client.get("/docs")
    assert resposta.status_code == 200
    assert "swagger-ui" in resposta.text.lower()


def test_redoc_disponivel():
    assert client.get("/redoc").status_code == 200


def test_raiz_redireciona_para_docs():
    resposta = client.get("/", follow_redirects=False)
    assert resposta.status_code in (302, 307)
    assert resposta.headers["location"] == "/docs"


def test_openapi_documenta_todos_os_endpoints():
    especificacao = client.get("/openapi.json").json()
    assert set(especificacao["paths"]) == CAMINHOS
    for caminho, metodos in especificacao["paths"].items():
        for metodo, operacao in metodos.items():
            assert operacao.get("summary"), f"{metodo.upper()} {caminho} sem summary"
            assert operacao.get("description"), f"{metodo.upper()} {caminho} sem description"
            assert operacao.get("tags"), f"{metodo.upper()} {caminho} sem tag"


def test_openapi_publica_o_contrato_usado_na_validacao():
    """Swagger e validacao leem a MESMA fonte: os modulos de schemas/v1/."""
    especificacao = client.get("/openapi.json").json()
    publicados = especificacao["components"]["schemas"]
    for nome, schema in componentes_openapi().items():
        assert publicados[nome] == schema, nome


def test_openapi_publica_um_componente_por_bloco_do_contrato():
    especificacao = client.get("/openapi.json").json()
    publicados = especificacao["components"]["schemas"]
    for nome in (
        "OperacaoCredito",
        "Cliente",
        "Cadastro",
        "Score",
        "Decisao",
        "Juros",
        "Financiamento",
        "OperacaoFinanceira",
        "ProdutoFinanceiro",
        "Promocao",
        "Credito",
        "Correlacao",
        "Documento",
        "Metadados",
    ):
        assert nome in publicados, nome


def test_corpo_do_post_referencia_o_contrato():
    especificacao = client.get("/openapi.json").json()
    corpo = especificacao["paths"]["/api/documentos"]["post"]["requestBody"]["content"][
        "application/json"
    ]
    assert corpo["schema"] == {"$ref": "#/components/schemas/OperacaoCredito"}


def test_swagger_traz_os_exemplos_de_cada_cenario():
    especificacao = client.get("/openapi.json").json()
    corpo = especificacao["paths"]["/api/documentos"]["post"]["requestBody"]["content"][
        "application/json"
    ]
    assert set(corpo["examples"]) == set(EXEMPLOS_OPERACAO)
    assert {"operacao_valida", "operacao_invalida"} <= set(corpo["examples"])
    for nome, dados in corpo["examples"].items():
        assert dados.get("summary"), f"exemplo {nome} sem summary"
        assert dados.get("description"), f"exemplo {nome} sem description"


def test_openapi_documenta_respostas_de_erro():
    especificacao = client.get("/openapi.json").json()
    post = especificacao["paths"]["/api/documentos"]["post"]["responses"]
    assert {"201", "400"} <= set(post)
    get = especificacao["paths"]["/api/documentos/{documento_id}"]["get"]["responses"]
    assert {"200", "404"} <= set(get)
    for nome in ("DocumentoCriado", "DocumentoMetadados", "ErroDadosInvalidos", "ErroNaoEncontrado"):
        assert nome in especificacao["components"]["schemas"]


def test_openapi_declara_a_versao_do_contrato():
    especificacao = client.get("/openapi.json").json()
    assert versao_contrato() in especificacao["info"]["description"]
    contrato = especificacao["components"]["schemas"]["OperacaoCredito"]
    assert contrato["x-versaoContrato"] == versao_contrato()


def test_contrato_publicado_descreve_os_campos():
    """Quem abre o Swagger precisa entender o que enviar sem perguntar."""
    especificacao = client.get("/openapi.json").json()
    schemas = especificacao["components"]["schemas"]
    for nome in ("OperacaoCredito", "Cliente", "Score", "OperacaoFinanceira"):
        assert schemas[nome].get("description"), f"{nome} sem description"
    score = schemas["Score"]
    assert score["properties"]["faixaRisco"]["enum"] == ["EXCELENTE", "BOM", "REGULAR", "CRITICO"]
    assert score["properties"]["scoreFinal"]["maximum"] == 1000
    assert "componentes" in score["required"]
