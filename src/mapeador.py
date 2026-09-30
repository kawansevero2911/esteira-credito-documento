"""Mapeamento do contrato canonico para o modelo documental.

Este modulo e o unico lugar do projeto que conhece ao mesmo tempo o contrato de
entrada e a estrutura do documento. Ele faz duas coisas:

1. escolhe quais secoes existem, a partir dos blocos efetivamente recebidos;
2. formata valores para leitura (moeda, data, percentual, CPF/CNPJ).

E o que ele NAO faz, porque pertence a outros processos da Esteira:

* nao calcula nem recalcula score, juros, decisao, risco, parcelas ou saldos;
* nao preenche campo ausente com valor padrao de negocio;
* nao converte a decisao de um grupo no vocabulario de outro.

Quando um bloco nao vem, a secao correspondente simplesmente nao aparece no
documento, e o que depende de alinhamento com outro grupo e listado como
pendencia no rodape - em vez de sair do PDF como se o dado nao existisse.

Sobre unidades de taxa: os grupos declararam unidades diferentes para a mesma
ideia. O grupo Financiamento de Imoveis informa percentual mensal (1.35 =
1,35% a.m.) e o grupo Controle Financeiro informa decimal (0.0199 = 1,99%
a.m.). A exibicao usa a equivalencia que o proprio grupo declarou, portanto e
conversao de unidade para leitura, nao calculo financeiro.
"""
from __future__ import annotations

from typing import Any

from .modelo_documental import (
    TEMPLATE_PADRAO,
    Campo,
    ModeloDocumental,
    Secao,
    Tabela,
)

TITULO_PADRAO = "Proposta de Operação de Crédito"

#: financiamento.tipo / produtoFinanceiro.categoria -> chave de template.
TEMPLATES_POR_PRODUTO = {
    "IMOBILIARIO": "proposta_imobiliaria",
    "FINANCIAMENTO_IMOVEL": "proposta_imobiliaria",
}

ROTULOS_TIPO_PESSOA = {"PF": "Pessoa física", "PJ": "Pessoa jurídica"}

ROTULOS_PRODUTO = {
    "FINANCIAMENTO_IMOVEL": "Financiamento de imóvel",
    "FINANCIAMENTO_AUTOMOVEL": "Financiamento de automóvel",
    "CREDITO_PESSOAL": "Crédito pessoal",
}

ROTULOS_FINANCIAMENTO = {
    "IMOBILIARIO": "Financiamento imobiliário",
    "AUTOMOTIVO": "Financiamento automotivo",
}

ROTULOS_PROCESSO = {
    "PROMOCOES_ACOES_CREDITO": "Promoções e Ações de Crédito",
    "CONTROLE_FINANCEIRO_OPERACOES": "Controle Financeiro de Operações",
    "CREDITO_PF_PJ": "Crédito PF e PJ",
    "FINANCIAMENTO_IMOVEIS": "Financiamento de Imóveis",
    "CALCULO_JUROS": "Cálculo de Juros",
    "ESTRUTURACAO_DOCUMENTOS": "Estruturação de Documentos",
    "PRODUTOS_FINANCEIROS": "Produtos Financeiros",
    "FINANCIAMENTO_AUTOMOTIVO": "Financiamento Automotivo",
    "DECISAO": "Decisão",
    "SCORE": "Score",
}

ROTULOS_DECISAO = {
    "APROVADA": "Aprovada",
    "APROVADO": "Aprovado",
    "RECUSADA": "Recusada",
    "ANALISE_MANUAL": "Análise manual",
}


# ------------------------------------------------------------------ formatacao

def formatar_moeda(valor: Any) -> str | None:
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return None
    inteiro, _, decimais = f"{valor:,.2f}".partition(".")
    return f"R$ {inteiro.replace(',', '.')},{decimais}"


def formatar_numero(valor: Any, casas: int = 2) -> str | None:
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return None
    return f"{valor:.{casas}f}".replace(".", ",")


def formatar_decimal(valor: Any, casas: int = 4) -> str | None:
    """Número decimal sem zeros à direita, com vírgula: 0.087 -> ``0,087``."""
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return None
    texto = f"{valor:.{casas}f}".rstrip("0").rstrip(".") or "0"
    return texto.replace(".", ",")


def formatar_percentual_de_percentual(valor: Any) -> str | None:
    """1.35 -> ``1,35% ao mês`` (unidade do grupo Financiamento de Imóveis)."""
    texto = formatar_numero(valor, 2)
    return None if texto is None else f"{texto}% ao mês"


def formatar_percentual_de_decimal(valor: Any) -> str | None:
    """0.0199 -> ``1,99% ao mês`` (unidade do grupo Controle Financeiro).

    Usa a equivalência declarada pelo próprio grupo; é conversão de unidade
    para exibição, não cálculo financeiro.
    """
    if not isinstance(valor, (int, float)) or isinstance(valor, bool):
        return None
    texto = f"{valor * 100:.4f}".rstrip("0").rstrip(".") or "0"
    return f"{texto.replace('.', ',')}% ao mês"


def formatar_data(valor: Any) -> str | None:
    """``2026-11-05`` -> ``05/11/2026``."""
    if not isinstance(valor, str) or len(valor) != 10:
        return None
    ano, _, resto = valor.partition("-")
    mes, _, dia = resto.partition("-")
    if not (ano and mes and dia):
        return None
    return f"{dia}/{mes}/{ano}"


def formatar_timestamp(valor: Any) -> str | None:
    """``2026-09-25T18:30:00Z`` -> ``25/09/2026 18:30 UTC``."""
    if not isinstance(valor, str) or "T" not in valor:
        return None
    data, _, hora = valor.partition("T")
    data_formatada = formatar_data(data)
    if data_formatada is None:
        return None
    return f"{data_formatada} {hora[:5]} UTC"


def formatar_cpf(valor: Any) -> str | None:
    if not isinstance(valor, str) or len(valor) != 11 or not valor.isdigit():
        return valor if isinstance(valor, str) else None
    return f"{valor[:3]}.{valor[3:6]}.{valor[6:9]}-{valor[9:]}"


def formatar_cnpj(valor: Any) -> str | None:
    if not isinstance(valor, str) or len(valor) != 14 or not valor.isdigit():
        return valor if isinstance(valor, str) else None
    return f"{valor[:2]}.{valor[2:5]}.{valor[5:8]}/{valor[8:12]}-{valor[12:]}"


def formatar_meses(valor: Any) -> str | None:
    if not isinstance(valor, int) or isinstance(valor, bool):
        return None
    return f"{valor} {'mês' if valor == 1 else 'meses'}"


def formatar_texto(valor: Any) -> str | None:
    if isinstance(valor, str):
        return valor or None
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, (int, float)):
        return str(valor)
    return None


# ----------------------------------------------------------------- utilitarios

def _bloco(operacao: dict, nome: str) -> dict:
    valor = operacao.get(nome)
    return valor if isinstance(valor, dict) else {}


def _montar(pares: list[tuple[str, Any]]) -> tuple[Campo, ...]:
    """Cria os campos, descartando os que nao vieram (valor ``None``)."""
    return tuple(Campo(rotulo, valor) for rotulo, valor in pares if valor is not None)


def _rotular(mapa: dict[str, str], valor: Any) -> str | None:
    if not isinstance(valor, str):
        return None
    return mapa.get(valor, valor)


# --------------------------------------------------------------------- secoes

def _secao_cliente(operacao: dict) -> Secao:
    cliente = _bloco(operacao, "cliente")
    contato = _bloco(cliente, "contato")
    endereco = _bloco(cliente, "endereco")
    tipo_pessoa = cliente.get("tipoPessoa")

    pares: list[tuple[str, Any]] = [
        ("Tipo de pessoa", _rotular(ROTULOS_TIPO_PESSOA, tipo_pessoa)),
    ]

    if tipo_pessoa == "PJ":
        dados = _bloco(cliente, "dadosPJ")
        pares += [
            ("Razão social", formatar_texto(dados.get("razaoSocial"))),
            ("Nome fantasia", formatar_texto(dados.get("nomeFantasia"))),
            ("CNPJ", formatar_cnpj(dados.get("cnpj"))),
        ]
    else:
        dados = _bloco(cliente, "dadosPF")
        pares += [
            ("Nome", formatar_texto(dados.get("nomeCompleto"))),
            ("CPF", formatar_cpf(dados.get("cpf"))),
            ("Data de nascimento", formatar_data(dados.get("dataNascimento"))),
            ("Idade", formatar_texto(dados.get("idade"))),
            ("Estado civil", formatar_texto(dados.get("estadoCivil"))),
            ("Dependentes", formatar_texto(dados.get("numeroDependentes"))),
        ]

    pares += [
        ("Telefone", formatar_texto(contato.get("telefone"))),
        ("E-mail", formatar_texto(contato.get("email"))),
        ("Endereço", _endereco_em_uma_linha(endereco)),
        ("CEP", formatar_texto(endereco.get("cep"))),
    ]
    return Secao("CLIENTE", _montar(pares))


def _endereco_em_uma_linha(endereco: dict) -> str | None:
    logradouro = endereco.get("logradouro")
    if not isinstance(logradouro, str) or not logradouro:
        cidade = endereco.get("cidade")
        return formatar_texto(cidade)

    partes = [logradouro]
    if endereco.get("numero"):
        partes.append(str(endereco["numero"]))
    if endereco.get("complemento"):
        partes.append(str(endereco["complemento"]))
    linha = ", ".join(partes)
    if endereco.get("bairro"):
        linha += f" — {endereco['bairro']}"
    cidade_estado = " / ".join(
        str(endereco[chave]) for chave in ("cidade", "estado") if endereco.get(chave)
    )
    if cidade_estado:
        linha += f" — {cidade_estado}"
    return linha


def _secao_produto(operacao: dict) -> Secao:
    produto = _bloco(operacao, "produtoFinanceiro")
    financiamento = _bloco(operacao, "financiamento")
    credito = _bloco(operacao, "credito")
    # O tipo de documento não entra aqui: já aparece no cabeçalho da página.
    pares: list[tuple[str, Any]] = [
        ("Categoria", _rotular(ROTULOS_PRODUTO, produto.get("categoria"))),
        ("Produto", formatar_texto(produto.get("nome"))),
        ("Código do produto", formatar_texto(produto.get("codigo"))),
        ("Modalidade", _rotular(ROTULOS_FINANCIAMENTO, financiamento.get("tipo"))),
        ("Finalidade", formatar_texto(credito.get("finalidade"))),
    ]
    return Secao("PRODUTO", _montar(pares))


def _secao_imovel(operacao: dict) -> Secao:
    financiamento = _bloco(operacao, "financiamento")
    if financiamento.get("tipo") != "IMOBILIARIO":
        return Secao("IMÓVEL", ())
    imovel = _bloco(financiamento, "imobiliario")
    pares: list[tuple[str, Any]] = [
        ("Tipo de imóvel", formatar_texto(imovel.get("tipoImovel"))),
        ("Cidade do imóvel", formatar_texto(imovel.get("cidade"))),
        ("Estado do imóvel", formatar_texto(imovel.get("estado"))),
        ("Valor do imóvel", formatar_moeda(imovel.get("valorImovel"))),
    ]
    return Secao("IMÓVEL", _montar(pares))


def _secao_perfil_financeiro(operacao: dict) -> Secao:
    cadastro = _bloco(operacao, "cadastro")
    pares: list[tuple[str, Any]] = [
        ("Renda mensal", formatar_moeda(cadastro.get("rendaMensal"))),
        ("Dívida total", formatar_moeda(cadastro.get("dividaTotal"))),
        ("Limite rotativo utilizado", formatar_moeda(cadastro.get("limiteRotativoUtilizado"))),
        ("Limite rotativo total", formatar_moeda(cadastro.get("limiteRotativoTotal"))),
        ("Dias de atraso (12 meses)", formatar_texto(cadastro.get("diasAtrasoUltimos12Meses"))),
        ("Tempo no emprego atual", formatar_meses(cadastro.get("mesesNoEmpregoAtual"))),
        ("Relacionamento com o banco", formatar_meses(cadastro.get("mesesRelacionamentoBanco"))),
    ]
    return Secao("FINANCEIRO — PERFIL DO CLIENTE", _montar(pares))


def _secao_condicoes(operacao: dict) -> Secao:
    credito = _bloco(operacao, "credito")
    juros = _bloco(operacao, "juros")
    financiamento = _bloco(operacao, "financiamento")
    imovel = _bloco(financiamento, "imobiliario")

    pares: list[tuple[str, Any]] = [
        ("Valor solicitado", formatar_moeda(credito.get("valorSolicitado"))),
        ("Prazo solicitado", formatar_meses(credito.get("prazoMeses"))),
        (
            "Taxa informada na solicitação",
            formatar_percentual_de_percentual(credito.get("taxaJurosMensalPercentual")),
        ),
        # O valor do imóvel fica na seção IMÓVEL; aqui começa pela entrada.
        ("Valor da entrada", formatar_moeda(imovel.get("valorEntrada"))),
        ("Valor financiado", formatar_moeda(imovel.get("valorFinanciado"))),
        ("Prazo do financiamento", formatar_meses(imovel.get("prazoMeses"))),
        (
            "Taxa de juros do financiamento",
            formatar_percentual_de_percentual(imovel.get("taxaJurosMensal")),
        ),
        ("Sistema de amortização", formatar_texto(imovel.get("sistemaAmortizacao"))),
        ("Primeira parcela", formatar_moeda(imovel.get("valorPrimeiraParcela"))),
        ("Última parcela", formatar_moeda(imovel.get("valorUltimaParcela"))),
        ("Total estimado de juros", formatar_moeda(imovel.get("totalJurosEstimado"))),
        ("Total estimado pago", formatar_moeda(imovel.get("totalPagoEstimado"))),
        ("Comprometimento da renda", formatar_decimal(imovel.get("comprometimentoRenda"))),
        ("Taxa calculada (Cálculo de Juros)", formatar_percentual_de_decimal(juros.get("taxaMensal"))),
        (
            "Sistema de amortização (Cálculo de Juros)",
            formatar_texto(juros.get("sistemaAmortizacao")),
        ),
    ]
    return Secao("FINANCEIRO — CONDIÇÕES DA OPERAÇÃO", _montar(pares))


def _secao_analise(operacao: dict) -> Secao:
    score = _bloco(operacao, "score")
    if not score:
        return Secao("ANÁLISE", ())
    modelo = _bloco(score, "modelo")
    componentes = score.get("componentes")
    fatores = score.get("fatoresImpacto")

    pares: list[tuple[str, Any]] = [
        ("Score final", formatar_texto(score.get("scoreFinal"))),
        ("Faixa de risco", formatar_texto(score.get("faixaRisco"))),
        ("Probabilidade de inadimplência", formatar_decimal(score.get("probabilidadeDefault"))),
        ("Modelo", formatar_texto(modelo.get("codigo"))),
        ("Versão do modelo", formatar_texto(modelo.get("versao"))),
        ("Origem do resultado", formatar_texto(score.get("origem"))),
        ("Calculado em", formatar_timestamp(score.get("calculatedAt"))),
    ]
    if isinstance(componentes, list):
        pares.append(("Componentes informados", str(len(componentes))))
    if isinstance(fatores, list):
        pares.append(("Fatores de impacto informados", str(len(fatores))))
    return Secao("ANÁLISE", _montar(pares))


def _secao_decisao(operacao: dict) -> Secao:
    decisao = _bloco(operacao, "decisao")
    if not decisao:
        return Secao("DECISÃO", ())
    motivos = decisao.get("motivos")
    pares: list[tuple[str, Any]] = [
        ("Resultado", _rotular(ROTULOS_DECISAO, decisao.get("resultado"))),
        ("Valor aprovado", formatar_moeda(decisao.get("valorAprovado"))),
        ("Data da aprovação", formatar_data(decisao.get("dataAprovacao"))),
        ("Decidido em", formatar_timestamp(decisao.get("decididoEm"))),
        ("Versão da política", formatar_texto(decisao.get("versaoPolitica"))),
    ]
    if isinstance(motivos, list) and motivos:
        for indice, motivo in enumerate(motivos, start=1):
            texto = formatar_texto(motivo)
            if texto is not None:
                pares.append((f"Motivo {indice}", texto))
    return Secao("DECISÃO", _montar(pares))


def _secao_operacao(operacao: dict) -> Secao:
    financeira = _bloco(operacao, "operacaoFinanceira")
    if not financeira:
        return Secao("OPERAÇÃO", ())
    pares: list[tuple[str, Any]] = [
        ("Número da operação", formatar_texto(financeira.get("numeroOperacao"))),
        ("Identificador interno", formatar_texto(financeira.get("id"))),
        ("Situação", formatar_texto(financeira.get("status"))),
        ("Valor aprovado", formatar_moeda(financeira.get("valorAprovado"))),
        ("Saldo devedor", formatar_moeda(financeira.get("saldoDevedor"))),
        ("Prazo", formatar_meses(financeira.get("prazo"))),
        ("Quantidade de parcelas", formatar_texto(financeira.get("quantidadeParcelas"))),
        ("Taxa de juros", formatar_percentual_de_decimal(financeira.get("taxaJuros"))),
        ("Sistema de amortização", formatar_texto(financeira.get("sistemaAmortizacao"))),
        ("Primeiro vencimento", formatar_data(financeira.get("primeiroVencimento"))),
        ("Data da aprovação", formatar_data(financeira.get("dataAprovacao"))),
        ("Criada em", formatar_timestamp(financeira.get("criadoEm"))),
    ]
    return Secao("OPERAÇÃO", _montar(pares))


def _secao_metadados(operacao: dict) -> Secao:
    metadados = _bloco(operacao, "metadados")
    correlacao = _bloco(operacao, "correlacao")
    participantes = metadados.get("processosParticipantes")

    pares: list[tuple[str, Any]] = [
        ("Versão do contrato", formatar_texto(operacao.get("schemaVersion"))),
        ("ID da operação", formatar_texto(correlacao.get("idOperacao"))),
        ("ID do cliente", formatar_texto(correlacao.get("idCliente"))),
        ("ID da proposta", formatar_texto(correlacao.get("idProposta"))),
        ("Origem da mensagem", _rotular(ROTULOS_PROCESSO, metadados.get("origem"))),
        ("Criado em", formatar_timestamp(metadados.get("criadoEm"))),
        ("Atualizado em", formatar_timestamp(metadados.get("atualizadoEm"))),
    ]
    if isinstance(participantes, list) and participantes:
        nomes = [ROTULOS_PROCESSO.get(item, str(item)) for item in participantes]
        pares.append(("Processos participantes", ", ".join(nomes)))
    return Secao("METADADOS", _montar(pares))


def _tabela_parcelas(operacao: dict) -> Tabela:
    cronograma = _bloco(operacao, "operacaoFinanceira").get("cronograma")
    if not isinstance(cronograma, list) or not cronograma:
        return Tabela("PARCELAS", (), ())

    linhas: list[tuple[str, ...]] = []
    for parcela in cronograma:
        if not isinstance(parcela, dict):
            continue
        linhas.append(
            (
                formatar_texto(parcela.get("numero")) or "",
                formatar_data(parcela.get("vencimento")) or "",
                formatar_moeda(parcela.get("valorParcela")) or "",
                formatar_moeda(parcela.get("valorAmortizacao")) or "",
                formatar_moeda(parcela.get("juros")) or "",
                formatar_moeda(parcela.get("saldoDevedorAposParcela")) or "",
                formatar_texto(parcela.get("status")) or "",
            )
        )

    return Tabela(
        titulo="PARCELAS",
        colunas=("Nº", "Vencimento", "Parcela", "Amortização", "Juros", "Saldo devedor", "Situação"),
        linhas=tuple(linhas),
        observacao=(
            "Cronograma informado pelo processo Controle Financeiro de Operações. "
            "Os valores não são recalculados por este serviço."
        ),
    )


# ------------------------------------------------------------------- pendencias

def _pendencias(operacao: dict) -> tuple[str, ...]:
    """Lista o que falta por depender de outro grupo, em vez de omitir em silêncio."""
    pendentes: list[str] = []
    if not _bloco(operacao, "score"):
        pendentes.append("Score não informado (processo Score).")
    if not _bloco(operacao, "decisao"):
        pendentes.append("Decisão não informada (processo Decisão).")
    if not _bloco(operacao, "juros"):
        pendentes.append("Cálculo de juros não informado (processo Cálculo de Juros).")
    if not _bloco(operacao, "operacaoFinanceira"):
        pendentes.append(
            "Operação financeira e cronograma não informados "
            "(processo Controle Financeiro de Operações)."
        )
    return tuple(pendentes)


def _destaques(operacao: dict) -> tuple[Campo, ...]:
    """Números do financiamento imobiliário que o template pode destacar."""
    financiamento = _bloco(operacao, "financiamento")
    if financiamento.get("tipo") != "IMOBILIARIO":
        return ()
    imovel = _bloco(financiamento, "imobiliario")
    pares: list[tuple[str, Any]] = [
        ("Valor do imóvel", formatar_moeda(imovel.get("valorImovel"))),
        ("Entrada", formatar_moeda(imovel.get("valorEntrada"))),
        ("Valor financiado", formatar_moeda(imovel.get("valorFinanciado"))),
        ("Prazo", formatar_meses(imovel.get("prazoMeses"))),
        ("Taxa de juros", formatar_percentual_de_percentual(imovel.get("taxaJurosMensal"))),
        ("Amortização", formatar_texto(imovel.get("sistemaAmortizacao"))),
    ]
    return _montar(pares)


def _escolher_template(operacao: dict) -> str:
    financiamento = _bloco(operacao, "financiamento")
    produto = _bloco(operacao, "produtoFinanceiro")
    for chave in (financiamento.get("tipo"), produto.get("categoria")):
        if isinstance(chave, str) and chave in TEMPLATES_POR_PRODUTO:
            return TEMPLATES_POR_PRODUTO[chave]
    return TEMPLATE_PADRAO


# ------------------------------------------------------------------- entrada

def mapear_para_modelo(operacao: dict) -> ModeloDocumental:
    """Converte a operação canônica validada no modelo documental."""
    documento = _bloco(operacao, "documento")
    correlacao = _bloco(operacao, "correlacao")
    titulo = documento.get("titulo")

    observacoes: list[str] = []
    texto_observacao = documento.get("observacoes")
    if isinstance(texto_observacao, str) and texto_observacao:
        observacoes.append(texto_observacao)

    secoes = (
        _secao_cliente(operacao),
        _secao_produto(operacao),
        _secao_imovel(operacao),
        _secao_perfil_financeiro(operacao),
        _secao_condicoes(operacao),
        _secao_analise(operacao),
        _secao_decisao(operacao),
        _secao_operacao(operacao),
        _secao_metadados(operacao),
    )

    return ModeloDocumental(
        titulo=titulo if isinstance(titulo, str) and titulo else TITULO_PADRAO,
        tipo_documento=str(documento.get("tipoDocumento", "")),
        id_operacao=str(correlacao.get("idOperacao", "")),
        versao_schema=str(operacao.get("schemaVersion", "")),
        chave_template=_escolher_template(operacao),
        secoes=secoes,
        tabelas=(_tabela_parcelas(operacao),),
        destaques=_destaques(operacao),
        observacoes=tuple(observacoes),
        pendencias=_pendencias(operacao),
    )


def mapear_para_template(operacao: dict) -> ModeloDocumental:
    """Nome usado até a versão 1.1.0. Mantido para não quebrar chamadas antigas."""
    return mapear_para_modelo(operacao)
