"""Validacao da entrada contra o contrato canonico (JSON Schema 2020-12).

A validacao e feita pela biblioteca ``jsonschema``, contra o contrato real -
nao ha regra de negocio reescrita em Python aqui. Duas extensoes foram
necessarias porque o JSON Schema padrao nao resolve os casos abaixo:

1. ``format``: por especificacao, ``format`` e apenas uma anotacao e a maioria
   dos validadores nao o verifica. Este modulo registra verificadores proprios,
   escritos so com a biblioteca padrao do Python, para ``date``, ``date-time``,
   ``uuid`` e ``email``. Assim ``2026-02-31`` e recusado como data inexistente,
   e nao apenas conferido no formato pelo ``pattern``.

2. ``x-casasDecimais``: o limite de casas decimais de valores monetarios e de
   taxas nao pode ser expresso com ``multipleOf``, porque ``multipleOf`` opera
   em ponto flutuante e recusa valores validos (1234.56 / 0.01 da
   123455.99999999999). A palavra-chave propria compara casas decimais em
   ``Decimal``, sem erro de arredondamento. Por ser uma extensao, validadores
   de outras linguagens a ignoram: o limite precisa ser respeitado pelo
   emissor. Ver docs/contrato-json.md.
"""
from __future__ import annotations

import datetime as _datetime
import json
import uuid as _uuid
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError
from jsonschema.validators import extend

# --------------------------------------------------------------- verificadores
# Construido vazio e preenchido so com os formatos que o contrato usa, para que
# o resultado da validacao nao dependa de bibliotecas opcionais instaladas na
# maquina de quem roda o servico.
VERIFICADOR_FORMATO = FormatChecker(formats=())


@VERIFICADOR_FORMATO.checks("date", raises=ValueError)
def _formato_data(valor: object) -> bool:
    if not isinstance(valor, str):
        return True
    _datetime.date.fromisoformat(valor)
    return True


@VERIFICADOR_FORMATO.checks("date-time", raises=ValueError)
def _formato_data_hora(valor: object) -> bool:
    if not isinstance(valor, str):
        return True
    _datetime.datetime.fromisoformat(valor)
    return True


@VERIFICADOR_FORMATO.checks("uuid", raises=ValueError)
def _formato_uuid(valor: object) -> bool:
    if not isinstance(valor, str):
        return True
    _uuid.UUID(valor)
    return True


@VERIFICADOR_FORMATO.checks("email")
def _formato_email(valor: object) -> bool:
    if not isinstance(valor, str):
        return True
    local, arroba, dominio = valor.partition("@")
    return bool(arroba) and bool(local) and "." in dominio and not dominio.startswith(".")


# ------------------------------------------------------- palavra-chave propria

def _x_casas_decimais(validator, casas, instance, schema):  # noqa: ANN001, ARG001
    """Recusa numeros com mais casas decimais do que o contrato permite."""
    if isinstance(instance, bool) or not isinstance(instance, (int, float)):
        return
    try:
        numero = Decimal(str(instance))
    except InvalidOperation:
        return
    if not numero.is_finite():
        return
    expoente = numero.as_tuple().exponent
    if not isinstance(expoente, int):
        return
    usadas = max(0, -expoente)
    if usadas > casas:
        yield ValidationError(
            f"{instance} possui {usadas} casas decimais; o maximo permitido e {casas}"
        )


#: Validador do projeto: Draft 2020-12 mais a palavra-chave ``x-casasDecimais``.
ValidadorContrato = extend(
    Draft202012Validator,
    validators={"x-casasDecimais": _x_casas_decimais},
)


class ErroValidacao(Exception):
    """Entrada que nao atende ao contrato.

    ``erros`` mantem o formato ``campo: motivo`` usado desde a versao 1.0.0.
    ``ocorrencias`` traz os mesmos problemas em forma estruturada, mais facil de
    tratar por quem integra em outra linguagem.
    """

    def __init__(self, erros: list[str], ocorrencias: list[dict[str, Any]] | None = None):
        self.erros = erros
        self.ocorrencias = ocorrencias or []
        super().__init__("; ".join(erros))


def carregar_schema(caminho: str | Path) -> dict:
    """Le um schema de arquivo.

    Mantido por compatibilidade. O contrato usado pelo servico e montado a
    partir dos modulos por ``src.contrato.carregar_contrato``.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _caminho_do_erro(erro: ValidationError) -> str:
    return ".".join(str(parte) for parte in erro.absolute_path) or "raiz"


def validar_operacao(dados: dict, schema: dict) -> None:
    """Valida ``dados`` contra ``schema``; levanta ``ErroValidacao`` se houver falha."""
    validador = ValidadorContrato(schema, format_checker=VERIFICADOR_FORMATO)

    erros: list[str] = []
    ocorrencias: list[dict[str, Any]] = []
    vistos: set[tuple[str, str]] = set()

    for erro in sorted(
        validador.iter_errors(dados),
        key=lambda item: (list(item.absolute_path), item.message),
    ):
        campo = _caminho_do_erro(erro)
        chave = (campo, erro.message)
        if chave in vistos:
            continue
        vistos.add(chave)
        erros.append(f"{campo}: {erro.message}")
        ocorrencias.append(
            {
                "campo": campo,
                "mensagem": erro.message,
                "regra": erro.validator,
            }
        )

    if erros:
        raise ErroValidacao(erros, ocorrencias)
