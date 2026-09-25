"""Gera docs/openapi.json a partir da API, sem precisar subir o servidor.

Uso (na raiz do projeto):
    python -m scripts.exportar_openapi

O arquivo gerado pode ser aberto em https://editor.swagger.io ou entregue
aos outros grupos como contrato da API.
"""
import json
from pathlib import Path

from src.api import app

DESTINO = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"


def main() -> None:
    DESTINO.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Especificação OpenAPI salva em {DESTINO}")


if __name__ == "__main__":
    main()
