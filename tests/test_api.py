def test_saude(client):
    r = client.get("/api/saude")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_criar_documento_valido(client, operacao_valida, storage):
    r = client.post("/api/documentos", json=operacao_valida)
    assert r.status_code == 201
    corpo = r.json()
    assert corpo["evento"]["evento"] == "documento.gerado"
    assert (storage / "pdfs" / f"{corpo['documento_id']}.pdf").exists()


def test_rejeita_invalida_com_400(client, operacao_invalida, storage):
    r = client.post("/api/documentos", json=operacao_invalida)
    assert r.status_code == 400
    corpo = r.json()
    assert corpo["codigo"] == "DADOS_INVALIDOS"
    assert len(corpo["erros"]) >= 3
    assert not list((storage / "pdfs").glob("*")) if (storage / "pdfs").exists() else True


def test_consultar_documento_criado(client, operacao_valida):
    doc_id = client.post("/api/documentos", json=operacao_valida).json()["documento_id"]
    r = client.get(f"/api/documentos/{doc_id}")
    assert r.status_code == 200
    assert r.json()["_id"] == doc_id
    assert r.json()["id_operacao"] == operacao_valida["id_operacao"]


def test_consultar_inexistente_404(client):
    r = client.get("/api/documentos/00000000-0000-4000-8000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"] == "Documento não encontrado"


def test_id_malformado_ou_traversal_404(client):
    assert client.get("/api/documentos/abc").status_code == 404
    assert client.get("/api/documentos/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_baixar_pdf(client, operacao_valida):
    doc_id = client.post("/api/documentos", json=operacao_valida).json()["documento_id"]
    r = client.get(f"/api/documentos/{doc_id}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF")


def test_pdf_inexistente_404(client):
    assert client.get("/api/documentos/00000000-0000-4000-8000-000000000000/pdf").status_code == 404


def test_endpoint_do_contrato(client):
    r = client.get("/api/schemas/operacao-credito")
    assert r.status_code == 200 and r.json()["title"] == "OperacaoCredito"


def test_documentacao_swagger(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/", follow_redirects=False).status_code in (302, 307)
    spec = client.get("/openapi.json").json()
    post = spec["paths"]["/api/documentos"]["post"]
    assert {"201", "400"} <= set(post["responses"])
    assert spec["info"]["version"] == "1.4.0"
