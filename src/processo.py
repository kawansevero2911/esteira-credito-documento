"""Orquestra o processo BPMN "Estruturação e Emissão de Documento da Operação de Crédito".

Início -> Validar estrutura -> [Dados válidos?] -não-> ErroValidacao (fim com erro)
                                              -sim-> Mapear -> Gerar PDF -> Armazenar -> Publicar evento -> Fim
"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft7Validator

from .gerador_pdf import gerar_pdf
from .mapeador import mapear_para_template
from .publicador_evento import PublicadorEventos
from .repositorio import RepositorioDocumentos
from .validador import validar_operacao


class ProcessoEmissaoDocumento:
    def __init__(self, schema: dict, repositorio: RepositorioDocumentos,
                 publicador: PublicadorEventos, diretorio_base: str | Path):
        Draft7Validator.check_schema(schema)
        self.schema = schema
        self.repositorio = repositorio
        self.publicador = publicador
        self.diretorio_pdfs = Path(diretorio_base) / "pdfs"

    def executar(self, operacao: dict) -> dict:
        # Tarefa "Validar estrutura" + gateway: levanta ErroValidacao antes de gerar qualquer coisa
        validar_operacao(operacao, self.schema)

        documento_id = str(uuid.uuid4())
        agora = datetime.now(timezone.utc)

        dados_template = mapear_para_template(operacao, agora)
        gerar_pdf(dados_template, self.diretorio_pdfs / f"{documento_id}.pdf")

        caminho_pdf = f"pdfs/{documento_id}.pdf"
        self.repositorio.salvar(documento_id, {
            "id_operacao": operacao["id_operacao"],
            "tipo_produto": operacao["tipo_produto"],
            "caminho_pdf": caminho_pdf,
            "tipo_documento": "PROPOSTA_CREDITO", "origem": "OPERACAO_CREDITO", "versao_schema": "v1",
        })

        evento = self.publicador.publicar({
            "evento": "documento.gerado",
            "id_operacao": operacao["id_operacao"],
            "documento_id": documento_id,
            "caminho_pdf": caminho_pdf,
            "tipo_documento": "PROPOSTA_CREDITO", "origem": "OPERACAO_CREDITO", "versao_schema": "v1",
        })

        return {
            "documento_id": documento_id,
            "resumo": {
                "id_operacao": operacao["id_operacao"],
                "tipo_produto": operacao["tipo_produto"],
                "cliente": operacao["cliente"]["nome"],
                "valor": operacao["valor"],
            },
            "evento": evento,
        }
