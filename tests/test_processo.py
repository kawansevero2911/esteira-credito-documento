import json

import pytest

from src.processo import ProcessoEmissaoDocumento
from src.publicador_evento import PublicadorArquivo
from src.repositorio import RepositorioArquivo
from src.validador import ErroValidacao


@pytest.fixture
def processo(schema, storage):
    return ProcessoEmissaoDocumento(schema, RepositorioArquivo(storage),
                                    PublicadorArquivo(storage, imprimir=False), storage)


def test_fluxo_completo(processo, operacao_valida, storage):
    resultado = processo.executar(operacao_valida)
    doc_id = resultado["documento_id"]

    pdf = storage / "pdfs" / f"{doc_id}.pdf"
    assert pdf.exists() and pdf.read_bytes().startswith(b"%PDF")
    assert (storage / "documentos" / f"{doc_id}.json").exists()

    linhas = (storage / "eventos" / "eventos.jsonl").read_text(encoding="utf-8").splitlines()
    evento = json.loads(linhas[-1])
    assert evento["evento"] == "documento.gerado"
    assert evento["documento_id"] == doc_id


def test_invalida_nao_gera_nada(processo, operacao_invalida, storage):
    with pytest.raises(ErroValidacao):
        processo.executar(operacao_invalida)
    assert not list((storage / "pdfs").glob("*")) if (storage / "pdfs").exists() else True
    assert not list((storage / "documentos").glob("*.json"))
    assert not (storage / "eventos" / "eventos.jsonl").exists()


def test_mesma_operacao_duas_vezes_gera_documentos_distintos(processo, operacao_valida):
    a = processo.executar(operacao_valida)["documento_id"]
    b = processo.executar(operacao_valida)["documento_id"]
    assert a != b
