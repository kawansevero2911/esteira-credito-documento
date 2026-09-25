from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from .processo import buscar_documento, executar_processo

app = FastAPI(
    title="Esteira de Crédito — Estruturação de Documentos",
    description=(
        "API responsável pela validação, estruturação, geração, armazenamento "
        "e disponibilização de documentos da Esteira de Crédito."
    ),
    version="1.0.0",
)


@app.get("/api/saude", tags=["Infraestrutura"])
def saude() -> dict:
    return {"status": "ok", "servico": "estruturacao-documentos"}


@app.post("/api/documentos", status_code=201, tags=["Documentos"])
def criar_documento(operacao: dict):
    resultado = executar_processo(operacao)
    if resultado["status"] == "erro":
        return JSONResponse(status_code=400, content=resultado)
    return resultado


@app.get("/api/documentos/{documento_id}", tags=["Documentos"])
def obter_documento(documento_id: str) -> dict:
    documento = buscar_documento(documento_id)
    if documento is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")
    return documento
