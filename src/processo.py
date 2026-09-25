from __future__ import annotations
import os
from pathlib import Path
from .gerador_pdf import gerar_pdf
from .mapeador import mapear_para_template
from .publicador_evento import publicar_documento_gerado
from .repositorio import RepositorioDocumentos
from .validador import ErroValidacao, carregar_schema, validar_operacao

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "schemas" / "operacao_credito.schema.json"
STORAGE_DIR = BASE_DIR / "storage"
PDF_DIR = STORAGE_DIR / "pdfs"
DOCUMENTOS_DIR = STORAGE_DIR / "documentos"
EVENTOS_DIR = STORAGE_DIR / "eventos"


def executar_processo(operacao: dict) -> dict:
    schema = carregar_schema(SCHEMA_PATH)
    try:
        validar_operacao(operacao, schema)
    except ErroValidacao as erro:
        return {
            "status": "erro",
            "codigo": "DADOS_INVALIDOS",
            "mensagem": "Os dados recebidos não atendem ao contrato JSON Schema.",
            "detalhes": erro.erros,
        }

    dados_template = mapear_para_template(operacao)
    caminho_pdf = PDF_DIR / f"{operacao['id_operacao']}.pdf"
    gerar_pdf(dados_template, str(caminho_pdf))

    repositorio = RepositorioDocumentos(str(DOCUMENTOS_DIR))
    doc_id = repositorio.salvar({
        "id_operacao": operacao["id_operacao"],
        "tipo_produto": operacao["tipo_produto"],
        "caminho_pdf": str(caminho_pdf),
    })

    evento = publicar_documento_gerado(
        doc_id,
        operacao["id_operacao"],
        str(caminho_pdf),
        str(EVENTOS_DIR),
    )

    return {
        "status": "sucesso",
        "documento_id": doc_id,
        "documento": {
            "id_operacao": operacao["id_operacao"],
            "tipo_produto": operacao["tipo_produto"],
            "caminho_pdf": str(caminho_pdf),
        },
        "evento": evento,
    }


def buscar_documento(documento_id: str) -> dict | None:
    return RepositorioDocumentos(str(DOCUMENTOS_DIR)).buscar(documento_id)
