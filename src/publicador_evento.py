"""Tarefa BPMN: "Publicar evento" (referência do documento).

`PublicadorEventos` é a PORTA. `PublicadorArquivo` registra o evento em JSON Lines
(e no terminal). Um adaptador de fila real (RabbitMQ, Kafka...) implementa o mesmo método.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol


class PublicadorEventos(Protocol):
    def publicar(self, evento: dict) -> dict: ...


class PublicadorArquivo:
    def __init__(self, diretorio_base: str | Path, imprimir: bool = True):
        self.diretorio = Path(diretorio_base) / "eventos"
        self.diretorio.mkdir(parents=True, exist_ok=True)
        self.imprimir = imprimir

    def publicar(self, evento: dict) -> dict:
        evento = {**evento, "publicado_em": datetime.now(timezone.utc).isoformat()}
        linha = json.dumps(evento, ensure_ascii=False)
        with open(self.diretorio / "eventos.jsonl", "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        if self.imprimir:
            print("[BARRAMENTO] Evento publicado:", linha)
        return evento
