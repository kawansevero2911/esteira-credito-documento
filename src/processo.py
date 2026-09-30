"""Orquestracao do processo documental.

Este modulo e o unico lugar que conhece a ORDEM do fluxo. Ele nao valida, nao
formata, nao desenha PDF e nao grava arquivo: chama, em sequencia, os modulos
que fazem cada coisa.

    receber -> (converter formato antigo) -> validar -> mapear -> gerar PDF
            -> armazenar -> publicar evento -> responder

A validacao acontece ANTES do mapeamento e da geracao do PDF, e a funcao retorna
imediatamente quando ela falha. Em consequencia, uma entrada invalida nao gera
PDF nem registro documental nem evento - o que e verificado por teste.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .compatibilidade import ErroConversaoLegado, normalizar_entrada
from .contrato import CAMINHO_BUNDLE, carregar_contrato, versao_contrato
from .gerador_pdf import gerar_pdf
from .mapeador import mapear_para_modelo
from .modelo_documental import ModeloDocumental
from .publicador_evento import (
    EventoDocumento,
    PublicadorArquivoJson,
    PublicadorEventos,
)
from .repositorio import (
    RegistroDocumento,
    RepositorioArquivosJson,
    RepositorioDocumentos,
)
from .validador import ErroValidacao, validar_operacao

BASE_DIR = Path(__file__).resolve().parent.parent

#: Contrato publicado. Mantido com o nome usado desde a versao 1.0.0 porque
#: scripts e outros grupos referenciam este caminho.
SCHEMA_PATH = CAMINHO_BUNDLE

STORAGE_DIR = BASE_DIR / "storage"
PDF_DIR = STORAGE_DIR / "pdfs"
DOCUMENTOS_DIR = STORAGE_DIR / "documentos"
EVENTOS_DIR = STORAGE_DIR / "eventos"

CODIGO_DADOS_INVALIDOS = "DADOS_INVALIDOS"
MENSAGEM_DADOS_INVALIDOS = "Os dados recebidos não atendem ao contrato JSON Schema."

_CARACTERES_SEGUROS = re.compile(r"[^A-Za-z0-9._-]")


def _nome_arquivo_pdf(id_operacao: str, documento_id: str) -> str:
    """Nome do PDF a partir do id da operacao, higienizado.

    O identificador vem de outro processo e nao tem formato padronizado, por
    isso qualquer caractere fora de letras, numeros, ponto, hifen e sublinhado e
    substituido: sem isso, um id como ``../../x`` escreveria fora da pasta de
    armazenamento. Se nada sobrar, o identificador do documento e usado.
    """
    seguro = _CARACTERES_SEGUROS.sub("_", id_operacao).strip("._-")
    return f"{seguro or documento_id}.pdf"


def _hash_arquivo(caminho: str) -> str:
    """SHA-256 do PDF emitido, para conferencia de integridade."""
    digestor = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(65536), b""):
            digestor.update(bloco)
    return f"sha256:{digestor.hexdigest()}"


def _tipo_produto(operacao: dict) -> str | None:
    """Rotulo curto do produto, para os metadados e para a resposta."""
    produto = operacao.get("produtoFinanceiro")
    if isinstance(produto, dict) and isinstance(produto.get("categoria"), str):
        return produto["categoria"]
    financiamento = operacao.get("financiamento")
    if isinstance(financiamento, dict) and isinstance(financiamento.get("tipo"), str):
        return financiamento["tipo"]
    return None


def _resposta_erro(
    detalhes: list[str],
    formato: str,
    ocorrencias: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "status": "erro",
        "codigo": CODIGO_DADOS_INVALIDOS,
        "mensagem": MENSAGEM_DADOS_INVALIDOS,
        "detalhes": detalhes,
        "erros": ocorrencias or [{"campo": "raiz", "mensagem": item, "regra": None} for item in detalhes],
        "formatoEntrada": formato,
        "versaoContrato": versao_contrato(),
    }


def executar_processo(
    operacao: Any,
    repositorio: RepositorioDocumentos | None = None,
    publicador: PublicadorEventos | None = None,
) -> dict[str, Any]:
    """Executa o fluxo documental completo para uma operacao recebida.

    ``repositorio`` e ``publicador`` podem ser injetados; por padrao usam o
    armazenamento local. Os diretorios sao lidos aqui, e nao no import, para que
    os testes possam redireciona-los.
    """
    # 1. Recebimento: aceita o contrato canonico e o formato plano da v1.0.0.
    try:
        canonica, formato = normalizar_entrada(operacao)
    except ErroConversaoLegado as erro:
        return _resposta_erro(erro.erros, "legado_v1")

    # 2. Validacao. Nada acontece depois daqui se a entrada for invalida.
    try:
        validar_operacao(canonica, carregar_contrato())
    except ErroValidacao as erro:
        return _resposta_erro(erro.erros, formato, erro.ocorrencias)

    # 3. Mapeamento para o modelo documental.
    modelo: ModeloDocumental = mapear_para_modelo(canonica)

    registro = RegistroDocumento(
        id_operacao=modelo.id_operacao,
        tipo_documento=modelo.tipo_documento,
        versao_schema=modelo.versao_schema,
        caminho_pdf="",
        tipo_produto=_tipo_produto(canonica),
        template=modelo.chave_template,
        correlacao=dict(canonica.get("correlacao") or {}),
    )

    # 4. Geracao do PDF.
    caminho_pdf = PDF_DIR / _nome_arquivo_pdf(modelo.id_operacao, registro.documento_id)
    gerar_pdf(modelo, str(caminho_pdf))
    registro.caminho_pdf = str(caminho_pdf)
    registro.hash_documento = _hash_arquivo(str(caminho_pdf))

    # 5. Armazenamento dos metadados.
    repositorio = repositorio or RepositorioArquivosJson(str(DOCUMENTOS_DIR))
    documento_id = repositorio.salvar(registro)

    # 6. Publicacao do evento.
    publicador = publicador or PublicadorArquivoJson(str(EVENTOS_DIR))
    evento = publicador.publicar(
        EventoDocumento(
            documento_id=documento_id,
            id_operacao=registro.id_operacao,
            tipo_documento=registro.tipo_documento,
            versao_schema=registro.versao_schema,
            caminho_pdf=registro.caminho_pdf,
            hash_documento=registro.hash_documento,
            correlacao=registro.correlacao,
        )
    )

    # 7. Resposta.
    return {
        "status": "sucesso",
        "documento_id": documento_id,
        "formatoEntrada": formato,
        "documento": {
            "documento_id": documento_id,
            "id_operacao": registro.id_operacao,
            "tipo_documento": registro.tipo_documento,
            "tipo_produto": registro.tipo_produto,
            "versao_schema": registro.versao_schema,
            "caminho_pdf": registro.caminho_pdf,
            "status": registro.status,
            "hash_documento": registro.hash_documento,
            "template": registro.template,
        },
        "evento": evento,
    }


def buscar_documento(documento_id: str) -> dict[str, Any] | None:
    """Consulta os metadados de um documento ja emitido."""
    return RepositorioArquivosJson(str(DOCUMENTOS_DIR)).buscar(documento_id)
