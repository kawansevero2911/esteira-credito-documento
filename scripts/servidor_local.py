"""Servidor de FUMACA, sem dependencias externas, para conferir o backend.

PARA QUE SERVE
--------------
O servico oficial e ``src/api.py`` (FastAPI), e e ele que traz o Swagger em
/docs e o OpenAPI em /openapi.json. Suba sempre o servico oficial quando
houver as dependencias instaladas:

    pip install -r requirements.txt
    uvicorn src.api:app --reload

Este script existe para o caso em que NAO da para instalar nada (maquina sem
acesso a rede, politica de proxy, apresentacao em sala). Ele sobe os mesmos
tres endpoints usando apenas a biblioteca padrao do Python, e serve o banco de
provas de web/index.html na raiz:

    python -m scripts.servidor_local
    # abrir http://127.0.0.1:8000/

Servir a pagina daqui resolve o CORS pela origem: pagina e API no mesmo
endereco. O servidor tambem responde aos cabecalhos de CORS, para o caso de a
pagina ser aberta direto do disco (file://).

LIMITES, PARA NAO CONFUNDIR
---------------------------
Este servidor NAO substitui o servico oficial e NAO deve ser usado em
integracao com os outros grupos. Ele nao tem Swagger, nao tem OpenAPI, nao
tem validacao de formato de corpo pelo framework e nao tem as respostas
tipadas de ``src/modelos.py``.

O que ele tem em comum com o servico oficial e o que importa aqui: a mesma
orquestracao. As duas camadas HTTP chamam ``src.processo.executar_processo`` e
``src.processo.buscar_documento`` e nao contem nenhuma regra de negocio
propria. Por isso o que este servidor responde e o mesmo que o FastAPI
responde no corpo: 201 com o documento, 400 DADOS_INVALIDOS sem gerar PDF,
200 na consulta e 404 quando o documento nao existe.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from src.processo import buscar_documento, executar_processo

BASE_DIR = Path(__file__).resolve().parents[1]
PAGINA = BASE_DIR / "web" / "index.html"

ENDERECO = "127.0.0.1"
PORTA = 8000

PREFIXO_DOCUMENTOS = "/api/documentos"


class Manipulador(BaseHTTPRequestHandler):
    """Roteamento minimo. Nenhuma regra de negocio mora aqui."""

    # Silencia o log linha-a-linha do BaseHTTPRequestHandler, que polui a saida.
    def log_message(self, formato: str, *args: object) -> None:  # noqa: A003
        return

    def _cors(self) -> None:
        """Libera a origem para o banco de provas aberto do disco.

        Permissivo de proposito: isto e ferramenta de teste local. Um servico
        exposto na rede deve restringir a origem.
        """
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _responder_json(self, status: int, corpo: dict) -> None:
        dados = json.dumps(corpo, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self._cors()
        self.end_headers()
        self.wfile.write(dados)

    def _responder_pagina(self) -> None:
        if not PAGINA.exists():
            self._responder_json(
                404,
                {
                    "detail": (
                        "web/index.html nao existe. Gere com "
                        "python -m scripts.gerar_frontend"
                    )
                },
            )
            return
        dados = PAGINA.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Resposta ao preflight do navegador."""
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        caminho = urlparse(self.path).path

        if caminho in ("/", "/index.html"):
            self._responder_pagina()
            return

        if caminho == "/api/saude":
            self._responder_json(200, {"status": "ok", "servico": "estruturacao-documentos"})
            return

        if caminho.startswith(f"{PREFIXO_DOCUMENTOS}/"):
            documento_id = caminho[len(PREFIXO_DOCUMENTOS) + 1 :]
            documento = buscar_documento(documento_id)
            if documento is None:
                self._responder_json(404, {"detail": "Documento não encontrado."})
            else:
                self._responder_json(200, documento)
            return

        self._responder_json(404, {"detail": "Rota não encontrada."})

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != PREFIXO_DOCUMENTOS:
            self._responder_json(404, {"detail": "Rota não encontrada."})
            return

        tamanho = int(self.headers.get("Content-Length") or 0)
        try:
            operacao = json.loads(self.rfile.read(tamanho) or b"null")
        except json.JSONDecodeError as erro:
            # O FastAPI devolveria 422 aqui; a mensagem e diferente, o efeito
            # e o mesmo: corpo que nao e JSON nao chega ao processo.
            self._responder_json(422, {"detail": f"Corpo não é JSON válido: {erro}"})
            return

        resultado = executar_processo(operacao)
        self._responder_json(400 if resultado["status"] == "erro" else 201, resultado)


def main() -> None:
    servidor = ThreadingHTTPServer((ENDERECO, PORTA), Manipulador)
    print(f"Servidor de fumaça em http://{ENDERECO}:{PORTA}")
    print(f"  banco de provas  http://{ENDERECO}:{PORTA}/")
    print("  endpoints        GET /api/saude · POST /api/documentos · GET /api/documentos/{id}")
    print("O serviço oficial, com Swagger, é: uvicorn src.api:app --reload")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
