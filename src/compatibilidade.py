"""Aceite do formato plano da versao 1.0.0 (compatibilidade retroativa).

O contrato v1.0.0 deste projeto era plano e em snake_case:

    {"id_operacao", "tipo_produto", "cliente": {"nome", "documento"},
     "valor", "prazo_meses", "taxa_juros_mensal"}

O contrato canonico 1.2.0 e hierarquico e em camelCase. Para nao quebrar quem
ja integrava, o ``POST /api/documentos`` aceita as duas formas: mensagens no
formato antigo sao CONVERTIDAS para o contrato canonico e so depois validadas.
Existe, portanto, um unico contrato e um unico ponto de validacao.

A deteccao e segura porque as duas formas nao se confundem: o contrato canonico
usa camelCase e exige ``schemaVersion``; o formato antigo usa snake_case e tem
``id_operacao`` na raiz.

Esta camada e um degrau de migracao, nao parte do contrato. Ver docs/contrato-json.md.
"""
from __future__ import annotations

from typing import Any

from .contrato import versao_contrato

FORMATO_CANONICO = "canonico"
FORMATO_LEGADO = "legado_v1"

#: Campos aceitos no formato antigo. Qualquer outro e recusado, como o schema
#: v1.0.0 fazia com ``additionalProperties: false``.
CAMPOS_LEGADO = {
    "id_operacao",
    "tipo_produto",
    "cliente",
    "valor",
    "prazo_meses",
    "taxa_juros_mensal",
}
CAMPOS_LEGADO_CLIENTE = {"nome", "documento"}

#: tipo_produto (v1.0.0) -> produtoFinanceiro.categoria (canonico).
CATEGORIAS_LEGADO = {
    "financiamento_imovel": "FINANCIAMENTO_IMOVEL",
    "financiamento_automovel": "FINANCIAMENTO_AUTOMOVEL",
    "credito_pessoal": "CREDITO_PESSOAL",
}


class ErroConversaoLegado(Exception):
    """Mensagem no formato antigo que nao pode ser convertida."""

    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("; ".join(erros))


def detectar_formato(dados: Any) -> str:
    """Diz se a mensagem esta no contrato canonico ou no formato antigo."""
    if not isinstance(dados, dict):
        return FORMATO_CANONICO
    if "schemaVersion" in dados or "correlacao" in dados:
        return FORMATO_CANONICO
    if "id_operacao" in dados:
        return FORMATO_LEGADO
    return FORMATO_CANONICO


def _somente_digitos(valor: str) -> str:
    return "".join(caractere for caractere in valor if caractere.isdigit())


def converter_legado(dados: dict) -> dict:
    """Converte uma mensagem v1.0.0 no contrato canonico.

    A conversao nao inventa dados: cada campo antigo vai para o bloco canonico
    equivalente, e campos ausentes continuam ausentes, de modo que a validacao
    reporte a falta deles normalmente.
    """
    desconhecidos = sorted(set(dados) - CAMPOS_LEGADO)
    if desconhecidos:
        raise ErroConversaoLegado(
            [
                f"raiz: campo '{campo}' nao existe no formato 1.0.0 nem no contrato canonico"
                for campo in desconhecidos
            ]
        )

    cliente_legado = dados.get("cliente")
    if cliente_legado is not None and not isinstance(cliente_legado, dict):
        raise ErroConversaoLegado(["cliente: deve ser um objeto"])
    cliente_legado = cliente_legado or {}

    desconhecidos_cliente = sorted(set(cliente_legado) - CAMPOS_LEGADO_CLIENTE)
    if desconhecidos_cliente:
        raise ErroConversaoLegado(
            [
                f"cliente: campo '{campo}' nao existe no formato 1.0.0"
                for campo in desconhecidos_cliente
            ]
        )

    # O formato antigo tinha um unico campo "documento" para CPF ou CNPJ. A
    # pontuacao e removida e a quantidade de digitos decide o tipo de pessoa;
    # se nao for 11 nem 14, o valor segue como CPF para que a validacao aponte
    # o erro no campo certo, em vez de a conversao decidir por conta propria.
    documento = cliente_legado.get("documento")
    nome = cliente_legado.get("nome")
    digitos = _somente_digitos(documento) if isinstance(documento, str) else None

    if digitos is not None and len(digitos) == 14:
        tipo_pessoa = "PJ"
        dados_pessoa: dict[str, Any] = {"cnpj": digitos}
        if nome is not None:
            dados_pessoa["razaoSocial"] = nome
        chave_pessoa = "dadosPJ"
    else:
        tipo_pessoa = "PF"
        dados_pessoa = {}
        if nome is not None:
            dados_pessoa["nomeCompleto"] = nome
        if documento is not None:
            dados_pessoa["cpf"] = digitos if digitos else documento
        chave_pessoa = "dadosPF"

    cliente: dict[str, Any] = {"tipoPessoa": tipo_pessoa}
    if dados_pessoa or documento is not None or nome is not None:
        cliente[chave_pessoa] = dados_pessoa

    credito: dict[str, Any] = {}
    if "valor" in dados:
        credito["valorSolicitado"] = dados["valor"]
    if "prazo_meses" in dados:
        credito["prazoMeses"] = dados["prazo_meses"]
    if "taxa_juros_mensal" in dados:
        credito["taxaJurosMensalPercentual"] = dados["taxa_juros_mensal"]

    canonico: dict[str, Any] = {
        "schemaVersion": versao_contrato(),
        "correlacao": {"idOperacao": dados.get("id_operacao")},
        "documento": {"tipoDocumento": "PROPOSTA_CREDITO"},
        "cliente": cliente,
    }

    tipo_produto = dados.get("tipo_produto")
    if tipo_produto is not None:
        categoria = CATEGORIAS_LEGADO.get(tipo_produto)
        # Um tipo_produto fora da lista vai adiante como esta, para que o enum
        # do contrato recuse o valor e a mensagem de erro cite o campo.
        canonico["produtoFinanceiro"] = {"categoria": categoria or tipo_produto}

    if credito:
        canonico["credito"] = credito

    return canonico


def normalizar_entrada(dados: Any) -> tuple[Any, str]:
    """Devolve ``(mensagem_canonica, formato_de_origem)``."""
    formato = detectar_formato(dados)
    if formato == FORMATO_LEGADO:
        return converter_legado(dados), formato
    return dados, formato
