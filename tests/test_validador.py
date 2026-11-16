import copy

import pytest

from src.validador import ErroValidacao, validar_operacao


def test_operacao_valida_passa(operacao_valida, schema):
    validar_operacao(operacao_valida, schema)


def _campos_com_erro(operacao, schema):
    with pytest.raises(ErroValidacao) as exc:
        validar_operacao(operacao, schema)
    return {e["campo"] for e in exc.value.erros}


def test_campo_obrigatorio_ausente(operacao_valida, schema):
    del operacao_valida["valor"]
    with pytest.raises(ErroValidacao) as exc:
        validar_operacao(operacao_valida, schema)
    assert any("valor" in e["mensagem"] for e in exc.value.erros)


def test_produto_fora_do_enum(operacao_valida, schema):
    operacao_valida["tipo_produto"] = "consorcio"
    assert "tipo_produto" in _campos_com_erro(operacao_valida, schema)


@pytest.mark.parametrize("valor", [-1, 0])
def test_valor_nao_positivo(operacao_valida, schema, valor):
    operacao_valida["valor"] = valor
    assert "valor" in _campos_com_erro(operacao_valida, schema)


@pytest.mark.parametrize("prazo", [0, -12, 12.5])
def test_prazo_invalido(operacao_valida, schema, prazo):
    operacao_valida["prazo_meses"] = prazo
    assert "prazo_meses" in _campos_com_erro(operacao_valida, schema)


def test_taxa_negativa(operacao_valida, schema):
    operacao_valida["taxa_juros_mensal"] = -0.1
    assert "taxa_juros_mensal" in _campos_com_erro(operacao_valida, schema)


def test_tipo_errado(operacao_valida, schema):
    operacao_valida["valor"] = "45000"
    assert "valor" in _campos_com_erro(operacao_valida, schema)


def test_campo_extra_rejeitado(operacao_valida, schema):
    operacao_valida["score"] = 800
    with pytest.raises(ErroValidacao):
        validar_operacao(operacao_valida, schema)


def test_campo_aninhado_do_cliente(operacao_valida, schema):
    operacao_valida = copy.deepcopy(operacao_valida)
    del operacao_valida["cliente"]["documento"]
    with pytest.raises(ErroValidacao) as exc:
        validar_operacao(operacao_valida, schema)
    assert any(e["campo"] == "cliente" for e in exc.value.erros)


def test_raiz_nao_objeto(schema):
    assert "raiz" in _campos_com_erro([1, 2], schema)
