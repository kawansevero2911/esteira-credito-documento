"""Regera schemas/operacao_credito.schema.json a partir de schemas/v1/.

Uso (na raiz do projeto):
    python -m scripts.gerar_bundle_schema

Rode este comando sempre que alterar qualquer arquivo de schemas/v1/. O teste
tests/test_contrato.py falha se o arquivo consolidado ficar diferente dos
modulos, justamente para que ninguem esqueca deste passo.
"""
from src.contrato import gravar_bundle, versao_contrato


def main() -> None:
    caminho = gravar_bundle()
    print(f"Contrato {versao_contrato()} consolidado em {caminho}")


if __name__ == "__main__":
    main()
