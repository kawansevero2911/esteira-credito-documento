from __future__ import annotations
import json
from pathlib import Path
from jsonschema import Draft202012Validator


class ErroValidacao(Exception):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("; ".join(erros))


def carregar_schema(caminho: str | Path) -> dict:
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def validar_operacao(dados: dict, schema: dict) -> None:
    validator = Draft202012Validator(schema)
    erros = []
    for erro in sorted(validator.iter_errors(dados), key=lambda item: list(item.path)):
        caminho = ".".join(str(parte) for parte in erro.path) or "raiz"
        erros.append(f"{caminho}: {erro.message}")
    if erros:
        raise ErroValidacao(erros)
