"""Tarefa BPMN: "Validar estrutura" (contra o JSON Schema, via biblioteca jsonschema)."""
from __future__ import annotations
from typing import Any

from jsonschema import Draft7Validator, FormatChecker


class ErroValidacao(Exception):
    """Levantada quando a operação não respeita o contrato (gateway 'Dados válidos?' = não)."""

    def __init__(self, erros: list[dict]):
        self.erros = erros
        super().__init__("; ".join(f"{e['campo']}: {e['mensagem']}" for e in erros))


def validar_operacao(dados: Any, schema: dict) -> None:
    validador = Draft7Validator(schema, format_checker=FormatChecker())
    erros = []
    for erro in sorted(validador.iter_errors(dados), key=lambda e: [str(p) for p in e.absolute_path]):
        campo = ".".join(str(p) for p in erro.absolute_path) or "raiz"
        erros.append({"campo": campo, "mensagem": erro.message})
    if erros:
        raise ErroValidacao(erros)
