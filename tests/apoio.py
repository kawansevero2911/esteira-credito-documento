"""Apoio compartilhado pelos testes.

Fica em um modulo comum (e nao no conftest.py) de proposito: assim as funcoes
tambem podem ser importadas por scripts que rodem os testes fora do pytest.
"""
from __future__ import annotations

import copy
import json
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parents[1]
EXEMPLOS = BASE / "examples"
SCHEMAS_V1 = BASE / "schemas" / "v1"


def exemplo(nome: str) -> dict[str, Any]:
    """Le um arquivo de examples/ (com ou sem a extensao .json)."""
    if not nome.endswith(".json"):
        nome = f"{nome}.json"
    return json.loads((EXEMPLOS / nome).read_text(encoding="utf-8"))


def operacao_minima() -> dict[str, Any]:
    """Menor operacao canonica valida: so os blocos obrigatorios."""
    return {
        "schemaVersion": "1.2.0",
        "correlacao": {"idOperacao": "OP-TESTE-0001"},
        "documento": {"tipoDocumento": "PROPOSTA_CREDITO"},
        "cliente": {
            "tipoPessoa": "PF",
            "dadosPF": {"nomeCompleto": "Cliente de Teste", "cpf": "12345678901"},
        },
    }


def score_valido() -> dict[str, Any]:
    """Bloco score completo, com todos os campos exigidos pelo grupo Score."""
    return {
        "scoreFinal": 742,
        "faixaRisco": "BOM",
        "probabilidadeDefault": 0.087,
        "modelo": {"codigo": "SCORE_PF", "versao": "v1.1.0"},
        "calculatedAt": "2026-09-25T18:30:00Z",
        "origem": "CALCULO",
        "componentes": [],
        "fatoresImpacto": [],
    }


def operacao_financeira_valida() -> dict[str, Any]:
    return {
        "id": "3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42",
        "numeroOperacao": "OP-2026-000123",
        "status": "ATIVA",
        "saldoDevedor": 320000.00,
        "taxaJuros": 0.0199,
        "sistemaAmortizacao": "PRICE",
        "primeiroVencimento": "2026-11-05",
        "criadoEm": "2026-09-25T18:31:00+00:00",
        "cronograma": [
            {
                "numero": 1,
                "vencimento": "2026-11-05",
                "valorParcela": 2800.00,
                "valorAmortizacao": 1500.00,
                "juros": 1300.00,
                "saldoDevedorAposParcela": 318500.00,
                "status": "PENDENTE",
            }
        ],
    }


def com_bloco(nome: str, conteudo: Any, base: dict | None = None) -> dict[str, Any]:
    """Copia a operacao base e acrescenta (ou substitui) um bloco."""
    operacao = copy.deepcopy(base) if base is not None else operacao_minima()
    operacao[nome] = copy.deepcopy(conteudo)
    return operacao


def alterar(operacao: dict, caminho: str, valor: Any) -> dict[str, Any]:
    """Copia e altera um campo aninhado. ``valor=None`` remove o campo.

    O caminho usa ``.`` como separador: ``"cliente.dadosPF.cpf"``.
    """
    copia = copy.deepcopy(operacao)
    partes = caminho.split(".")
    alvo = copia
    for parte in partes[:-1]:
        alvo = alvo[parte]
    if valor is None:
        alvo.pop(partes[-1], None)
    else:
        alvo[partes[-1]] = valor
    return copia


def campos_com_erro(erro) -> set[str]:
    """Conjunto dos campos citados em um ``ErroValidacao``."""
    return {ocorrencia["campo"] for ocorrencia in erro.ocorrencias}


@contextmanager
def armazenamento_temporario():
    """Redireciona o armazenamento do processo para uma pasta descartavel.

    Usado no lugar das fixtures do pytest nos testes que nao dependem do
    FastAPI, para que eles possam ser executados por qualquer runner.
    """
    from src import processo

    diretorio = Path(tempfile.mkdtemp(prefix="esteira-teste-"))
    originais = {
        nome: getattr(processo, nome)
        for nome in ("STORAGE_DIR", "PDF_DIR", "DOCUMENTOS_DIR", "EVENTOS_DIR")
    }
    processo.STORAGE_DIR = diretorio
    processo.PDF_DIR = diretorio / "pdfs"
    processo.DOCUMENTOS_DIR = diretorio / "documentos"
    processo.EVENTOS_DIR = diretorio / "eventos"
    try:
        yield diretorio
    finally:
        for nome, valor in originais.items():
            setattr(processo, nome, valor)
        shutil.rmtree(diretorio, ignore_errors=True)
