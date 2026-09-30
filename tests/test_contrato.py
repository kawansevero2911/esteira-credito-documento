"""Testes do contrato: modulos, consolidacao e publicacao no OpenAPI."""
from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from src.contrato import (
    CAMINHO_BUNDLE,
    componentes_openapi,
    construir_bundle,
    versao_contrato,
)
from tests.apoio import SCHEMAS_V1

BLOCOS_ESPERADOS = {
    "correlacao",
    "documento",
    "cliente",
    "cadastro",
    "promocao",
    "credito",
    "produtoFinanceiro",
    "financiamento",
    "score",
    "juros",
    "decisao",
    "operacaoFinanceira",
    "metadados",
}


def test_versao_do_contrato_e_a_linha_1x():
    versao = versao_contrato()
    assert versao == "1.2.0"
    assert versao.startswith("1.")


def test_bundle_e_um_json_schema_valido():
    """O contrato consolidado tem de passar pelo meta-schema do Draft 2020-12."""
    Draft202012Validator.check_schema(construir_bundle())


def test_bundle_publicado_esta_sincronizado_com_os_modulos():
    """schemas/operacao_credito.schema.json e gerado de schemas/v1/.

    Se este teste falhar, alguem alterou um modulo e esqueceu de rodar
    `python -m scripts.gerar_bundle_schema`.
    """
    publicado = json.loads(CAMINHO_BUNDLE.read_text(encoding="utf-8"))
    assert publicado == construir_bundle(), (
        "O contrato publicado esta diferente dos modulos. "
        "Rode: python -m scripts.gerar_bundle_schema"
    )


def test_contrato_tem_um_bloco_por_area_da_esteira():
    bundle = construir_bundle()
    assert BLOCOS_ESPERADOS <= set(bundle["properties"])


def test_apenas_o_essencial_e_obrigatorio_globalmente():
    """Nenhum processo deve ser obrigado a enviar bloco que nao e dele."""
    bundle = construir_bundle()
    assert bundle["required"] == ["schemaVersion", "correlacao", "documento", "cliente"]


def test_contrato_recusa_bloco_desconhecido():
    assert construir_bundle()["additionalProperties"] is False


def test_blocos_sem_contrato_definido_ficam_abertos():
    """Bloco cujo contrato o grupo ainda nao forneceu aceita campos extras.

    E o oposto de inventar campos: a area existe, mas nada e exigido nem
    recusado ate o grupo responsavel definir o contrato.
    """
    defs = construir_bundle()["$defs"]
    for bloco in ("promocao", "credito", "juros", "decisao"):
        assert defs[bloco].get("additionalProperties") is True, bloco
    assert defs["financiamento"]["properties"]["automotivo"]["additionalProperties"] is True
    assert defs["cliente"]["properties"]["dadosPJ"]["additionalProperties"] is True


def test_blocos_com_contrato_definido_sao_estritos():
    defs = construir_bundle()["$defs"]
    for bloco in ("cliente", "cadastro", "score", "operacao_financeira", "correlacao", "metadados"):
        assert defs[bloco].get("additionalProperties") is False, bloco


def test_pendencias_estao_documentadas_no_proprio_schema():
    """Quem le so o schema precisa saber o que ainda depende de outro grupo."""
    defs = construir_bundle()["$defs"]
    for bloco in ("promocao", "credito", "juros", "decisao"):
        assert "PENDENCIA" in defs[bloco]["description"], bloco


def test_todo_modulo_declara_title_e_description():
    for arquivo in sorted(SCHEMAS_V1.glob("*.schema.json")):
        schema = json.loads(arquivo.read_text(encoding="utf-8"))
        assert schema.get("title"), f"{arquivo.name} sem title"
        assert schema.get("description"), f"{arquivo.name} sem description"
        assert schema.get("$schema"), f"{arquivo.name} sem $schema"
        assert schema.get("$id"), f"{arquivo.name} sem $id"


def test_openapi_publica_um_componente_por_bloco():
    componentes = componentes_openapi()
    assert "OperacaoCredito" in componentes
    for nome in ("Cliente", "Score", "Decisao", "Juros", "Financiamento", "OperacaoFinanceira"):
        assert nome in componentes, nome


def test_referencias_do_openapi_resolvem():
    """Nenhum $ref pode apontar para um componente inexistente."""
    componentes = componentes_openapi()
    documento = {"components": {"schemas": componentes}}

    def percorrer(no):
        if isinstance(no, dict):
            for chave, valor in no.items():
                if chave == "$ref" and isinstance(valor, str):
                    yield valor
                else:
                    yield from percorrer(valor)
        elif isinstance(no, list):
            for item in no:
                yield from percorrer(item)

    def resolver(ponteiro: str):
        no = documento
        for parte in ponteiro.removeprefix("#/").split("/"):
            if not isinstance(no, dict) or parte not in no:
                return None
            no = no[parte]
        return no

    referencias = list(percorrer(componentes))
    assert referencias, "o contrato deveria ter referencias entre blocos"
    for referencia in referencias:
        assert referencia.startswith("#/components/schemas/"), referencia
        assert resolver(referencia) is not None, f"referencia quebrada: {referencia}"


def test_componentes_do_openapi_nao_carregam_escopo_proprio():
    """$schema e $id criariam um escopo de resolucao dentro do OpenAPI."""
    for nome, schema in componentes_openapi().items():
        assert "$schema" not in schema, nome
        assert "$id" not in schema, nome
