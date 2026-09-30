"""Testes do aceite do formato plano da versao 1.0.0.

O objetivo e garantir que quem ja integrava com o contrato antigo continue
funcionando, e que a conversao nao invente dado nenhum.
"""
from __future__ import annotations

from src.compatibilidade import (
    FORMATO_CANONICO,
    FORMATO_LEGADO,
    ErroConversaoLegado,
    converter_legado,
    detectar_formato,
    normalizar_entrada,
)
from src.contrato import carregar_contrato
from src.validador import ErroValidacao, validar_operacao
from tests.apoio import exemplo, operacao_minima

CONTRATO = carregar_contrato()

LEGADO = {
    "id_operacao": "OP-2026-000123",
    "tipo_produto": "financiamento_automovel",
    "cliente": {"nome": "Cliente Exemplo", "documento": "000.000.000-00"},
    "valor": 45000.0,
    "prazo_meses": 48,
    "taxa_juros_mensal": 1.35,
}


def test_deteccao_do_formato():
    assert detectar_formato(LEGADO) == FORMATO_LEGADO
    assert detectar_formato(operacao_minima()) == FORMATO_CANONICO
    assert detectar_formato(exemplo("legado_v1_plano")) == FORMATO_LEGADO
    assert detectar_formato({}) == FORMATO_CANONICO


def test_mensagem_legada_vira_contrato_canonico_valido():
    canonica, formato = normalizar_entrada(LEGADO)
    assert formato == FORMATO_LEGADO
    validar_operacao(canonica, CONTRATO)


def test_conversao_preserva_os_dados_do_formato_antigo():
    canonica = converter_legado(LEGADO)
    assert canonica["correlacao"]["idOperacao"] == "OP-2026-000123"
    assert canonica["produtoFinanceiro"]["categoria"] == "FINANCIAMENTO_AUTOMOVEL"
    assert canonica["cliente"]["dadosPF"]["nomeCompleto"] == "Cliente Exemplo"
    assert canonica["credito"]["valorSolicitado"] == 45000.0
    assert canonica["credito"]["prazoMeses"] == 48
    assert canonica["credito"]["taxaJurosMensalPercentual"] == 1.35
    assert canonica["documento"]["tipoDocumento"] == "PROPOSTA_CREDITO"


def test_pontuacao_do_documento_e_removida():
    assert converter_legado(LEGADO)["cliente"]["dadosPF"]["cpf"] == "00000000000"


def test_documento_com_14_digitos_vira_pessoa_juridica():
    legado = dict(LEGADO, cliente={"nome": "Empresa Exemplo", "documento": "12.345.678/0001-99"})
    canonica = converter_legado(legado)
    assert canonica["cliente"]["tipoPessoa"] == "PJ"
    assert canonica["cliente"]["dadosPJ"]["cnpj"] == "12345678000199"
    assert canonica["cliente"]["dadosPJ"]["razaoSocial"] == "Empresa Exemplo"
    validar_operacao(canonica, CONTRATO)


def test_conversao_nao_preenche_campo_ausente():
    """Campo que faltava no formato antigo continua faltando: a validacao acusa."""
    legado = {"id_operacao": "OP-1", "cliente": {"nome": "Sem documento"}}
    canonica = converter_legado(legado)
    assert "cpf" not in canonica["cliente"]["dadosPF"]
    try:
        validar_operacao(canonica, CONTRATO)
    except ErroValidacao as erro:
        assert any("cpf" in item for item in erro.erros)
        return
    raise AssertionError("deveria ter sido recusada por falta de CPF")


def test_documento_com_quantidade_estranha_de_digitos_e_recusado_pela_validacao():
    """A conversao nao decide por conta propria: o erro aparece no campo CPF."""
    legado = dict(LEGADO, cliente={"nome": "X", "documento": "123"})
    canonica = converter_legado(legado)
    try:
        validar_operacao(canonica, CONTRATO)
    except ErroValidacao as erro:
        assert any("cliente.dadosPF.cpf" in item for item in erro.erros)
        return
    raise AssertionError("deveria ter sido recusada")


def test_tipo_de_produto_desconhecido_chega_a_validacao():
    legado = dict(LEGADO, tipo_produto="consorcio")
    canonica = converter_legado(legado)
    assert canonica["produtoFinanceiro"]["categoria"] == "consorcio"
    try:
        validar_operacao(canonica, CONTRATO)
    except ErroValidacao as erro:
        assert any("produtoFinanceiro.categoria" in item for item in erro.erros)
        return
    raise AssertionError("deveria ter sido recusada pelo enum de categoria")


def test_campo_fora_do_formato_antigo_e_recusado():
    """O schema v1.0.0 recusava campo desconhecido; a conversao mantem isso."""
    for legado, trecho in (
        (dict(LEGADO, campoInventado=1), "campoInventado"),
        (dict(LEGADO, cliente={"nome": "X", "documento": "00000000000", "rg": "1"}), "rg"),
    ):
        try:
            converter_legado(legado)
        except ErroConversaoLegado as erro:
            assert any(trecho in item for item in erro.erros)
            continue
        raise AssertionError(f"deveria ter recusado {trecho}")


def test_cliente_precisa_ser_objeto():
    try:
        converter_legado(dict(LEGADO, cliente="Cliente Exemplo"))
    except ErroConversaoLegado as erro:
        assert "cliente" in erro.erros[0]
        return
    raise AssertionError("deveria ter recusado cliente que nao e objeto")


def test_mensagem_canonica_passa_intacta():
    operacao = operacao_minima()
    resultado, formato = normalizar_entrada(operacao)
    assert formato == FORMATO_CANONICO
    assert resultado == operacao
