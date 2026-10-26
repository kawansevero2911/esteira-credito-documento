"""Leitura de PDF: extrai texto e metadados de um documento existente.

O resto do Processo 6 vai no sentido JSON -> PDF. Este modulo faz o caminho
de volta: recebe um PDF (emitido aqui ou enviado por outro processo) e devolve
o texto de cada pagina, os metadados e o hash de integridade.

Usos previstos:

- conferir que o PDF emitido contem o que deveria (cliente, operacao, valores);
- conferir que um PDF nao foi alterado desde a emissao, comparando o hash com o
  ``hash_documento`` gravado nos metadados;
- ler documentos enviados por outros grupos.

A biblioteca de leitura e o ``pypdf`` (pura em Python, sem dependencia de
sistema). A extracao de texto funciona para PDFs gerados por programa, como os
deste projeto; PDFs escaneados sao imagens e exigiriam OCR, fora do escopo.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .processo import _hash_arquivo

#: Assinatura que todo arquivo PDF traz nos primeiros bytes.
ASSINATURA_PDF = b"%PDF"


class ErroLeituraPdf(Exception):
    """O arquivo nao existe, nao e um PDF ou nao pode ser lido."""


@dataclass
class ConteudoPdf:
    """Resultado da leitura de um PDF."""

    caminho: str
    paginas: list[str]
    metadados: dict[str, str] = field(default_factory=dict)
    hash_documento: str = ""

    @property
    def numero_paginas(self) -> int:
        return len(self.paginas)

    @property
    def texto(self) -> str:
        """Texto de todas as paginas, separadas por uma linha em branco."""
        return "\n\n".join(self.paginas)

    def contem(self, trecho: str) -> bool:
        """Indica se o trecho aparece no texto, ignorando espacos extras."""
        return " ".join(trecho.split()) in " ".join(self.texto.split())

    def como_dict(self) -> dict[str, Any]:
        return {
            "caminho": self.caminho,
            "numero_paginas": self.numero_paginas,
            "metadados": self.metadados,
            "hash_documento": self.hash_documento,
            "paginas": self.paginas,
        }


def _conferir_arquivo(caminho: Path) -> None:
    if not caminho.is_file():
        raise ErroLeituraPdf(f"Arquivo não encontrado: {caminho}")
    with open(caminho, "rb") as arquivo:
        inicio = arquivo.read(1024)
    # A especificacao permite lixo antes do cabecalho, por isso procura no
    # primeiro kilobyte em vez de exigir que comece exatamente com %PDF.
    if ASSINATURA_PDF not in inicio:
        raise ErroLeituraPdf(f"O arquivo não é um PDF: {caminho}")


def _metadados(leitor: PdfReader) -> dict[str, str]:
    """Metadados do PDF com nomes legiveis (titulo, autor, assunto...)."""
    brutos = leitor.metadata or {}
    nomes = {
        "/Title": "titulo",
        "/Author": "autor",
        "/Subject": "assunto",
        "/Creator": "criador",
        "/Producer": "produtor",
        "/CreationDate": "criado_em",
        "/ModDate": "modificado_em",
    }
    return {
        nomes.get(chave, chave.lstrip("/")): str(valor)
        for chave, valor in brutos.items()
        if valor not in (None, "")
    }


def ler_pdf(caminho: str | Path, senha: str | None = None) -> ConteudoPdf:
    """Le o PDF em ``caminho`` e devolve texto por pagina, metadados e hash.

    ``senha`` so e necessaria para PDFs protegidos. Levanta ``ErroLeituraPdf``
    quando o arquivo nao existe, nao e PDF, esta corrompido ou protegido.
    """
    caminho = Path(caminho)
    _conferir_arquivo(caminho)

    try:
        leitor = PdfReader(str(caminho))
        if leitor.is_encrypted:
            # PDFs com protecao "so de permissao" abrem com senha vazia.
            if not leitor.decrypt(senha or ""):
                raise ErroLeituraPdf(f"PDF protegido por senha: {caminho}")
        paginas = [(pagina.extract_text() or "").strip() for pagina in leitor.pages]
        metadados = _metadados(leitor)
    except ErroLeituraPdf:
        raise
    except (PdfReadError, ValueError, KeyError, OSError) as erro:
        raise ErroLeituraPdf(f"Não foi possível ler o PDF {caminho}: {erro}") from erro

    return ConteudoPdf(
        caminho=str(caminho),
        paginas=paginas,
        metadados=metadados,
        hash_documento=_hash_arquivo(str(caminho)),
    )


def conferir_integridade(caminho: str | Path, hash_esperado: str) -> bool:
    """Indica se o PDF continua igual ao emitido.

    ``hash_esperado`` e o ``hash_documento`` gravado nos metadados do documento,
    no formato ``sha256:<hex>``.
    """
    caminho = Path(caminho)
    _conferir_arquivo(caminho)
    return _hash_arquivo(str(caminho)) == hash_esperado
