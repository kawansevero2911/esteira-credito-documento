"""Testes da validacao da entrada contra o contrato canonico.

Cada teste cobre uma regra que os grupos da Esteira declararam. Quando um caso
e recusado, o teste confere TAMBEM em qual campo o erro foi apontado: uma
mensagem generica nao ajudaria quem esta integrando.
"""
from __future__ import annotations

from src.contrato import carregar_contrato
from src.validador import ErroValidacao, validar_operacao
from tests.apoio import (
    alterar,
    campos_com_erro,
    com_bloco,
    exemplo,
    operacao_financeira_valida,
    operacao_minima,
    score_valido,
)

CONTRATO = carregar_contrato()

FINANCIAMENTO_IMOBILIARIO = {
    "tipo": "IMOBILIARIO",
    "imobiliario": {
        "valorImovel": 400000.00,
        "valorEntrada": 80000.00,
        "prazoMeses": 360,
        "taxaJurosMensal": 0.95,
        "sistemaAmortizacao": "SAC",
    },
}


def operacao_imobiliaria() -> dict:
    operacao = operacao_minima()
    operacao["cliente"]["dadosPF"]["dataNascimento"] = "1990-05-12"
    operacao["cliente"]["endereco"] = {"logradouro": "Rua Exemplo", "cidade": "Recife"}
    operacao["cadastro"] = {"rendaMensal": 8500.00}
    operacao["financiamento"] = FINANCIAMENTO_IMOBILIARIO
    return operacao


def aceita(operacao: dict) -> None:
    validar_operacao(operacao, CONTRATO)


def recusa(operacao: dict, campo: str) -> ErroValidacao:
    """Confere que a operacao e recusada E que o erro aponta o campo certo."""
    try:
        validar_operacao(operacao, CONTRATO)
    except ErroValidacao as erro:
        assert campo in campos_com_erro(erro), (
            f"esperava erro em {campo!r}, vieram: {sorted(campos_com_erro(erro))}"
        )
        return erro
    raise AssertionError(f"a operacao deveria ter sido recusada por causa de {campo!r}")


# --------------------------------------------------------------- casos validos

def test_operacao_minima_e_valida():
    aceita(operacao_minima())


def test_financiamento_imobiliario_completo_e_valido():
    aceita(operacao_imobiliaria())


def test_todos_os_exemplos_validos_passam():
    for nome in (
        "operacao_valida",
        "operacao_com_score",
        "operacao_com_decisao",
        "operacao_completa",
        "operacao_credito_pj",
    ):
        aceita(exemplo(nome))


def test_exemplo_invalido_e_recusado():
    try:
        validar_operacao(exemplo("operacao_invalida"), CONTRATO)
    except ErroValidacao as erro:
        assert len(erro.erros) >= 10, "o exemplo invalido deveria concentrar varios erros"
        return
    raise AssertionError("o exemplo invalido deveria ter sido recusado")


# ------------------------------------------------------- campos obrigatorios

def test_campo_obrigatorio_ausente():
    for bloco in ("schemaVersion", "correlacao", "documento", "cliente"):
        recusa(alterar(operacao_minima(), bloco, None), "raiz")


def test_id_da_operacao_e_obrigatorio():
    recusa(alterar(operacao_minima(), "correlacao.idOperacao", None), "correlacao")


def test_bloco_desconhecido_na_raiz_e_recusado():
    recusa(com_bloco("blocoInventado", {"x": 1}), "raiz")


def test_campo_desconhecido_em_bloco_estrito_e_recusado():
    recusa(alterar(operacao_minima(), "cliente.apelido", "x"), "cliente")


# ------------------------------------------------------------------- versao

def test_versao_do_contrato_fora_da_linha_1x():
    recusa(alterar(operacao_minima(), "schemaVersion", "2.0.0"), "schemaVersion")


def test_versao_do_contrato_mal_formada():
    recusa(alterar(operacao_minima(), "schemaVersion", "1.2"), "schemaVersion")


# ---------------------------------------------------------------------- CPF

def test_cpf_precisa_ter_11_digitos():
    for invalido in ("123.456.789-01", "1234567890", "123456789012", "1234567890a"):
        recusa(alterar(operacao_minima(), "cliente.dadosPF.cpf", invalido), "cliente.dadosPF.cpf")


def test_cpf_com_11_digitos_e_aceito():
    aceita(alterar(operacao_minima(), "cliente.dadosPF.cpf", "00000000000"))


# ------------------------------------------------------------- PF, PJ e nomes

def test_tipo_pessoa_invalido():
    recusa(alterar(operacao_minima(), "cliente.tipoPessoa", "PFJ"), "cliente.tipoPessoa")


def test_pessoa_fisica_exige_dados_pf():
    operacao = operacao_minima()
    operacao["cliente"] = {"tipoPessoa": "PF"}
    recusa(operacao, "cliente")


def test_pessoa_fisica_exige_nome_e_cpf():
    recusa(alterar(operacao_minima(), "cliente.dadosPF.nomeCompleto", None), "cliente.dadosPF")
    recusa(alterar(operacao_minima(), "cliente.dadosPF.cpf", None), "cliente.dadosPF")


def test_pessoa_juridica_exige_dados_pj():
    operacao = operacao_minima()
    operacao["cliente"] = {"tipoPessoa": "PJ"}
    recusa(operacao, "cliente")


def test_pessoa_juridica_nao_exige_campo_interno():
    """O contrato de PJ ainda nao foi definido: nada pode ser exigido dentro."""
    operacao = operacao_minima()
    operacao["cliente"] = {"tipoPessoa": "PJ", "dadosPJ": {}}
    aceita(operacao)


def test_pessoa_juridica_aceita_campos_ainda_nao_definidos():
    operacao = operacao_minima()
    operacao["cliente"] = {"tipoPessoa": "PJ", "dadosPJ": {"inscricaoEstadual": "123"}}
    aceita(operacao)


# ------------------------------------------------------------ datas e horarios

def test_data_inexistente_no_calendario():
    recusa(
        alterar(operacao_minima(), "cliente.dadosPF.dataNascimento", "2026-02-31"),
        "cliente.dadosPF.dataNascimento",
    )


def test_data_em_formato_errado():
    for invalida in ("12/05/1990", "1990-5-12", "19900512"):
        recusa(
            alterar(operacao_minima(), "cliente.dadosPF.dataNascimento", invalida),
            "cliente.dadosPF.dataNascimento",
        )


def test_data_valida_e_aceita():
    aceita(alterar(operacao_minima(), "cliente.dadosPF.dataNascimento", "2024-02-29"))


def test_timestamp_precisa_ser_utc():
    base = com_bloco("score", score_valido())
    for invalido in (
        "2026-09-25T18:30:00",
        "2026-09-25T18:30:00-03:00",
        "2026-09-25 18:30:00Z",
        "25/09/2026T18:30:00Z",
    ):
        recusa(alterar(base, "score.calculatedAt", invalido), "score.calculatedAt")


def test_timestamp_invalido_no_relogio():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.calculatedAt", "2026-09-25T25:30:00Z"), "score.calculatedAt")


def test_timestamp_utc_e_aceito_nas_duas_formas():
    base = com_bloco("score", score_valido())
    aceita(alterar(base, "score.calculatedAt", "2026-09-25T18:30:00Z"))
    aceita(alterar(base, "score.calculatedAt", "2026-09-25T18:30:00+00:00"))
    aceita(alterar(base, "score.calculatedAt", "2026-09-25T18:30:00.123456Z"))


# -------------------------------------------------------------------- score

def test_score_fora_da_faixa_0_a_1000():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.scoreFinal", 1001), "score.scoreFinal")
    recusa(alterar(base, "score.scoreFinal", -1), "score.scoreFinal")


def test_score_nos_limites_da_faixa():
    base = com_bloco("score", score_valido())
    aceita(alterar(base, "score.scoreFinal", 0))
    aceita(alterar(base, "score.scoreFinal", 1000))


def test_score_precisa_ser_inteiro():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.scoreFinal", 742.5), "score.scoreFinal")


def test_faixa_de_risco_invalida():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.faixaRisco", "OTIMO"), "score.faixaRisco")


def test_origem_do_score_invalida():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.origem", "CACHE"), "score.origem")


def test_modelo_do_score_invalido():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.modelo.codigo", "SCORE_XX"), "score.modelo.codigo")


def test_modelo_do_score_precisa_combinar_com_o_tipo_de_pessoa():
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.modelo.codigo", "SCORE_PJ"), "score.modelo.codigo")


def test_score_exige_componentes_e_fatores_impacto():
    """O grupo Score exige que as duas listas EXISTAM na saida."""
    base = com_bloco("score", score_valido())
    recusa(alterar(base, "score.componentes", None), "score")
    recusa(alterar(base, "score.fatoresImpacto", None), "score")


def test_arrays_vazios_sao_permitidos_quando_especificado():
    """componentes e fatoresImpacto podem estar vazios; o cronograma tambem."""
    base = com_bloco("score", score_valido())
    aceita(alterar(alterar(base, "score.componentes", []), "score.fatoresImpacto", []))

    operacao = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    aceita(alterar(operacao, "operacaoFinanceira.cronograma", []))

    aceita(com_bloco("decisao", {"resultado": "APROVADA", "motivos": []}))
    aceita(com_bloco("metadados", {"processosParticipantes": []}))


def test_componente_do_score_nao_exige_campos():
    """O grupo Score disse que cada componente PODE ter esses campos."""
    base = com_bloco("score", score_valido())
    aceita(alterar(base, "score.componentes", [{}, {"nome": "Renda"}]))


# ------------------------------------------------------------------ decisao

def test_decisao_invalida():
    recusa(com_bloco("decisao", {"resultado": "PENDENTE"}), "decisao.resultado")


def test_decisao_exige_resultado():
    recusa(com_bloco("decisao", {"motivos": ["x"]}), "decisao")


def test_decisao_aceita_os_vocabularios_dos_dois_grupos():
    """Divergencia real entre os grupos; os dois valores sao aceitos por ora."""
    for resultado in ("APROVADA", "RECUSADA", "ANALISE_MANUAL", "APROVADO"):
        aceita(com_bloco("decisao", {"resultado": resultado}))


# ---------------------------------------------------- financiamento por produto

def test_sistema_de_amortizacao_invalido():
    operacao = operacao_imobiliaria()
    recusa(
        alterar(operacao, "financiamento.imobiliario.sistemaAmortizacao", "SACRE"),
        "financiamento.imobiliario.sistemaAmortizacao",
    )


def test_sistema_de_amortizacao_aceita_sac_e_price():
    operacao = operacao_imobiliaria()
    for sistema in ("SAC", "PRICE"):
        aceita(alterar(operacao, "financiamento.imobiliario.sistemaAmortizacao", sistema))


def test_tipo_de_financiamento_invalido():
    recusa(com_bloco("financiamento", {"tipo": "CONSIGNADO"}), "financiamento.tipo")


def test_financiamento_exige_tipo():
    recusa(com_bloco("financiamento", {"imobiliario": {}}), "financiamento")


def test_imobiliario_exige_os_campos_declarados_pelo_grupo():
    operacao = operacao_imobiliaria()
    for campo in ("valorImovel", "valorEntrada", "prazoMeses", "taxaJurosMensal", "sistemaAmortizacao"):
        recusa(
            alterar(operacao, f"financiamento.imobiliario.{campo}", None),
            "financiamento.imobiliario",
        )


def test_imobiliario_exige_renda_e_endereco():
    recusa(alterar(operacao_imobiliaria(), "cadastro.rendaMensal", None), "cadastro")
    recusa(alterar(operacao_imobiliaria(), "cliente.endereco", None), "cliente")
    recusa(alterar(operacao_imobiliaria(), "cliente.endereco.cidade", None), "cliente.endereco")


def test_imobiliario_pf_exige_data_de_nascimento():
    recusa(
        alterar(operacao_imobiliaria(), "cliente.dadosPF.dataNascimento", None),
        "cliente.dadosPF",
    )


def test_automotivo_nao_exige_dados_imobiliarios():
    """O contrato do automotivo ainda nao existe: nada pode ser exigido dentro."""
    aceita(com_bloco("financiamento", {"tipo": "AUTOMOTIVO", "automotivo": {}}))
    aceita(com_bloco("financiamento", {"tipo": "AUTOMOTIVO", "automotivo": {"modelo": "X"}}))


def test_automotivo_exige_apenas_o_proprio_bloco():
    recusa(com_bloco("financiamento", {"tipo": "AUTOMOTIVO"}), "financiamento")


def test_prazo_precisa_ser_inteiro_positivo():
    operacao = operacao_imobiliaria()
    recusa(alterar(operacao, "financiamento.imobiliario.prazoMeses", 0), "financiamento.imobiliario.prazoMeses")
    recusa(alterar(operacao, "financiamento.imobiliario.prazoMeses", 12.5), "financiamento.imobiliario.prazoMeses")


def test_valor_monetario_nao_pode_ser_negativo():
    operacao = operacao_imobiliaria()
    recusa(
        alterar(operacao, "financiamento.imobiliario.valorImovel", -1.0),
        "financiamento.imobiliario.valorImovel",
    )


# ---------------------------------------------------------- casas decimais

def test_valor_monetario_aceita_no_maximo_2_casas():
    operacao = operacao_imobiliaria()
    aceita(alterar(operacao, "financiamento.imobiliario.valorImovel", 400000.12))
    recusa(
        alterar(operacao, "financiamento.imobiliario.valorImovel", 400000.123),
        "financiamento.imobiliario.valorImovel",
    )


def test_taxa_decimal_aceita_no_maximo_6_casas():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    aceita(alterar(base, "operacaoFinanceira.taxaJuros", 0.019999))
    recusa(alterar(base, "operacaoFinanceira.taxaJuros", 0.0199999), "operacaoFinanceira.taxaJuros")


def test_valores_inteiros_passam_na_regra_de_casas_decimais():
    operacao = operacao_imobiliaria()
    aceita(alterar(operacao, "financiamento.imobiliario.valorImovel", 400000))


# ------------------------------------------------------- operacao financeira

def test_numero_da_operacao_segue_o_padrao_do_grupo():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    aceita(alterar(base, "operacaoFinanceira.numeroOperacao", "OP-2026-000001"))
    for invalido in ("OP-26-000001", "OP-2026-1", "2026-000001", "op-2026-000001"):
        recusa(alterar(base, "operacaoFinanceira.numeroOperacao", invalido), "operacaoFinanceira.numeroOperacao")


def test_status_da_operacao_so_aceita_o_estado_informado():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    recusa(alterar(base, "operacaoFinanceira.status", "QUITADA"), "operacaoFinanceira.status")


def test_parcela_precisa_estar_completa():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    recusa(
        alterar(base, "operacaoFinanceira.cronograma", [{"numero": 1, "vencimento": "2026-11-05"}]),
        "operacaoFinanceira.cronograma.0",
    )


def test_status_da_parcela_so_aceita_o_estado_informado():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    parcela = dict(operacao_financeira_valida()["cronograma"][0], status="PAGA")
    recusa(
        alterar(base, "operacaoFinanceira.cronograma", [parcela]),
        "operacaoFinanceira.cronograma.0.status",
    )


def test_identificador_uuid_invalido():
    base = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    recusa(alterar(base, "operacaoFinanceira.id", "nao-e-uuid"), "operacaoFinanceira.id")


# ----------------------------------------------------------------- metadados

def test_processo_participante_invalido():
    recusa(com_bloco("metadados", {"processosParticipantes": ["OUTRO"]}), "metadados.processosParticipantes.0")


def test_metadados_completos_sao_aceitos():
    aceita(
        com_bloco(
            "metadados",
            {
                "origem": "SCORE",
                "criadoEm": "2026-09-25T18:00:00Z",
                "atualizadoEm": "2026-09-25T18:05:00Z",
                "processosParticipantes": ["SCORE", "DECISAO"],
            },
        )
    )


# ------------------------------------------------------------ forma do erro

def test_erro_traz_campo_mensagem_e_regra():
    erro = recusa(alterar(operacao_minima(), "cliente.dadosPF.cpf", "abc"), "cliente.dadosPF.cpf")
    ocorrencia = next(o for o in erro.ocorrencias if o["campo"] == "cliente.dadosPF.cpf")
    assert ocorrencia["regra"] == "pattern"
    assert ocorrencia["mensagem"]
    assert len(erro.erros) == len(erro.ocorrencias)
    assert all(": " in item for item in erro.erros)


def test_erros_nao_vem_repetidos():
    erro = recusa(exemplo("operacao_invalida"), "score.scoreFinal")
    assert len(erro.erros) == len(set(erro.erros))
