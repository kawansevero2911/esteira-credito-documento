"""Carga, consolidacao e versionamento do contrato canonico.

O contrato e escrito em MODULOS, um por bloco, em ``schemas/v1/``. Essa e a
fonte da verdade: cada grupo da Esteira mexe no arquivo do seu bloco sem
precisar abrir um arquivo gigante.

Para publicar o contrato (Swagger/OpenAPI, entrega aos outros grupos, uso por
validadores de outras linguagens) os modulos sao consolidados em UM arquivo
auto-contido, em ``schemas/operacao_credito.schema.json``. Esse arquivo e
gerado por ``scripts/gerar_bundle_schema.py`` e fica versionado no repositorio
para que o caminho publico do contrato nao mude e para que quem so quer o
contrato nao precise executar nada.

A consolidacao transforma cada modulo em uma entrada de ``$defs`` e reescreve
as referencias entre arquivos:

    "cliente.schema.json"                       -> "#/$defs/cliente"
    "comuns.schema.json#/$defs/valorMonetario"  -> "#/$defs/comuns/$defs/valorMonetario"

Assim o mesmo contrato funciona em duas formas: modular para manutencao e
consolidado para publicacao.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent

#: Pasta dos modulos da linha 1.x do contrato. Uma futura linha incompativel
#: entra em ``schemas/v2/`` sem apagar esta.
DIR_MODULOS = BASE_DIR / "schemas" / "v1"

#: Arquivo raiz do contrato modular.
ARQUIVO_RAIZ = "operacao_credito.schema.json"

#: Contrato consolidado e publicado. Caminho preservado desde a versao 1.0.0.
CAMINHO_BUNDLE = BASE_DIR / "schemas" / "operacao_credito.schema.json"

SUFIXO = ".schema.json"


class ErroContrato(Exception):
    """Falha ao carregar ou consolidar os modulos do contrato."""


def _nome_modulo(arquivo: str) -> str:
    """``operacao_financeira.schema.json`` -> ``operacao_financeira``."""
    if not arquivo.endswith(SUFIXO):
        raise ErroContrato(f"Referencia fora do padrao *{SUFIXO}: {arquivo!r}")
    return arquivo[: -len(SUFIXO)]


def _ler_modulo(nome: str) -> dict[str, Any]:
    caminho = DIR_MODULOS / f"{nome}{SUFIXO}"
    if not caminho.exists():
        raise ErroContrato(f"Modulo do contrato nao encontrado: {caminho}")
    with open(caminho, encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _reescrever_refs(no: Any, dependencias: set[str]) -> Any:
    """Troca refs entre arquivos por ponteiros internos e coleta dependencias.

    Percorre a arvore inteira porque ``$ref`` pode aparecer em qualquer
    profundidade (``properties``, ``items``, ``$defs``, ``if``/``then``,
    ``allOf``...).
    """
    if isinstance(no, dict):
        resultado: dict[str, Any] = {}
        for chave, valor in no.items():
            if chave == "$ref" and isinstance(valor, str) and not valor.startswith("#"):
                arquivo, _, fragmento = valor.partition("#")
                nome = _nome_modulo(arquivo)
                dependencias.add(nome)
                resultado[chave] = f"#/$defs/{nome}{fragmento}"
            else:
                resultado[chave] = _reescrever_refs(valor, dependencias)
        return resultado
    if isinstance(no, list):
        return [_reescrever_refs(item, dependencias) for item in no]
    return no


def construir_bundle() -> dict[str, Any]:
    """Consolida os modulos de ``schemas/v1/`` em um schema auto-contido.

    Parte do arquivo raiz e segue as referencias em largura, de modo que um
    modulo novo passa a ser incluido apenas por ser referenciado - nao existe
    lista de modulos para manter em dia.
    """
    raiz = _reescrever_refs(_ler_modulo(_nome_modulo(ARQUIVO_RAIZ)), pendentes := set())

    defs: dict[str, Any] = {}
    while pendentes:
        nome = pendentes.pop()
        if nome in defs:
            continue
        novas: set[str] = set()
        modulo = _reescrever_refs(_ler_modulo(nome), novas)
        # $schema e $id so valem para um documento independente; dentro de
        # $defs eles criariam um novo escopo de resolucao de referencias.
        modulo.pop("$schema", None)
        modulo.pop("$id", None)
        defs[nome] = modulo
        pendentes |= novas - defs.keys()

    bundle = dict(raiz)
    # Os modulos entram depois dos $defs que a raiz eventualmente tenha.
    bundle["$defs"] = {**raiz.get("$defs", {}), **dict(sorted(defs.items()))}
    return bundle


def carregar_contrato() -> dict[str, Any]:
    """Contrato usado pela validacao e pela publicacao no OpenAPI.

    Construido a partir dos modulos, e nao do arquivo consolidado, para que a
    validacao nunca use uma versao desatualizada do bundle. A sincronia entre
    os dois e garantida por teste.
    """
    return construir_bundle()


def versao_contrato() -> str:
    """Versao do contrato, lida do proprio schema (fonte unica da verdade)."""
    versao = _ler_modulo(_nome_modulo(ARQUIVO_RAIZ)).get("x-versaoContrato")
    if not isinstance(versao, str) or not versao:
        raise ErroContrato(
            f"O arquivo {ARQUIVO_RAIZ} nao declara x-versaoContrato."
        )
    return versao


def _nome_componente(modulo: str, schema: dict[str, Any]) -> str:
    """Nome do modulo como componente do OpenAPI, a partir do seu ``title``."""
    titulo = schema.get("title")
    if isinstance(titulo, str) and titulo:
        return titulo
    return "".join(parte.capitalize() for parte in modulo.split("_"))


def _apontar_para_componentes(no: Any, nomes: dict[str, str]) -> Any:
    """Troca ``#/$defs/<modulo>`` por ``#/components/schemas/<Nome>``.

    Dentro do OpenAPI, ``#`` aponta para a raiz do documento, e nao para o
    schema onde a referencia aparece. Sem esta reescrita, cada ``$ref`` do
    contrato consolidado apontaria para um ``$defs`` inexistente na raiz do
    OpenAPI e o Swagger nao conseguiria montar os modelos.
    """
    if isinstance(no, dict):
        resultado: dict[str, Any] = {}
        for chave, valor in no.items():
            if chave == "$ref" and isinstance(valor, str) and valor.startswith("#/$defs/"):
                partes = valor[len("#/$defs/") :].split("/")
                modulo, resto = partes[0], partes[1:]
                destino = nomes.get(modulo, modulo)
                sufixo = "/" + "/".join(resto) if resto else ""
                resultado[chave] = f"#/components/schemas/{destino}{sufixo}"
            else:
                resultado[chave] = _apontar_para_componentes(valor, nomes)
        return resultado
    if isinstance(no, list):
        return [_apontar_para_componentes(item, nomes) for item in no]
    return no


def componentes_openapi() -> dict[str, dict[str, Any]]:
    """Publica o contrato como componentes nomeados do OpenAPI.

    Cada bloco vira um modelo com nome proprio (Cliente, Score, Decisao...) em
    vez de um unico objeto gigante embutido: no Swagger, quem integra consegue
    abrir bloco por bloco e ver campos, tipos, enums e obrigatoriedade.

    Os campos ``$schema`` e ``$id`` sao removidos porque criariam um escopo de
    resolucao proprio dentro do documento OpenAPI.
    """
    bundle = construir_bundle()
    modulos: dict[str, Any] = bundle.pop("$defs", {})

    nomes = {modulo: _nome_componente(modulo, schema) for modulo, schema in modulos.items()}

    raiz = dict(bundle)
    raiz.pop("$schema", None)
    raiz.pop("$id", None)
    nome_raiz = _nome_componente(_nome_modulo(ARQUIVO_RAIZ), raiz)

    componentes: dict[str, dict[str, Any]] = {
        nome_raiz: _apontar_para_componentes(raiz, nomes)
    }
    for modulo, schema in modulos.items():
        componentes[nomes[modulo]] = _apontar_para_componentes(schema, nomes)
    return componentes


def gravar_bundle() -> Path:
    """Regrava ``schemas/operacao_credito.schema.json`` a partir dos modulos."""
    conteudo = json.dumps(construir_bundle(), ensure_ascii=False, indent=2)
    CAMINHO_BUNDLE.write_text(conteudo + "\n", encoding="utf-8")
    return CAMINHO_BUNDLE
