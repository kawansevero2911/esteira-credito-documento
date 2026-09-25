from __future__ import annotations
import json
import os
from datetime import datetime, timezone


def publicar_documento_gerado(doc_id: str, id_operacao: str, caminho_pdf: str, diretorio: str) -> dict:
    """Registra o evento localmente; o barramento real será integrado depois."""
    evento = {
        "evento": "documento.gerado",
        "id_operacao": id_operacao,
        "documento_id": doc_id,
        "caminho_pdf": caminho_pdf,
        "publicado_em": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(diretorio, exist_ok=True)
    caminho = os.path.join(diretorio, f"{doc_id}.json")
    with open(caminho, "w", encoding="utf-8") as arquivo:
        json.dump(evento, arquivo, ensure_ascii=False, indent=2)
    return evento
