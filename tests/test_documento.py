"""Testes do mapeamento, da geracao do PDF, do armazenamento e do evento.

Estes testes exercitam o fluxo do Processo 6 sem passar pelo HTTP, para separar
falha de regra documental de falha de API.
"""
from __future__ import annotations

from pathlib import Path

from src import processo
from src.mapeador import (
    formatar_cnpj,
    formatar_cpf,
    formatar_data,
    formatar_moeda,
    formatar_percentual_de_decimal,
    formatar_timestamp,
    mapear_para_modelo,
)
from src.modelo_documental import TEMPLATE_PADRAO
from src.publicador_evento import EventoDocumento, PublicadorArquivoJson
from src.repositorio import RegistroDocumento, RepositorioArquivosJson
from src.templates_pdf import TEMPLATES, obter_template
from tests.apoio import (
    armazenamento_temporario,
    com_bloco,
    exemplo,
    operacao_financeira_valida,
    operacao_minima,
    score_valido,
)


# --------------------------------------------------------------- formatacao

def test_formatacao_para_leitura():
    assert formatar_moeda(1234567.5) == "R$ 1.234.567,50"
    assert formatar_moeda(0) == "R$ 0,00"
    assert formatar_moeda("x") is None
    assert formatar_data("2026-11-05") == "05/11/2026"
    assert formatar_data("05/11/2026") is None
    assert formatar_timestamp("2026-09-25T18:30:00Z") == "25/09/2026 18:30 UTC"
    assert formatar_cpf("12345678901") == "123.456.789-01"
    assert formatar_cnpj("12345678000199") == "12.345.678/0001-99"


def test_taxa_decimal_e_exibida_em_percentual():
    """0.0199 = 1,99% ao mes, equivalencia declarada pelo grupo Controle Financeiro."""
    assert formatar_percentual_de_decimal(0.0199) == "1,99% ao mês"
    assert formatar_percentual_de_decimal(0.01) == "1% ao mês"


# ------------------------------------------------------------- mapeamento

def test_modelo_traz_apenas_as_secoes_recebidas():
    modelo = mapear_para_modelo(operacao_minima())
    titulos = {secao.titulo for secao in modelo.secoes_preenchidas}
    assert "CLIENTE" in titulos
    for ausente in ("ANÁLISE", "DECISÃO", "OPERAÇÃO"):
        assert ausente not in titulos, f"{ausente} nao deveria aparecer sem o bloco correspondente"


def test_modelo_traz_as_secoes_de_cada_bloco_recebido():
    modelo = mapear_para_modelo(exemplo("operacao_completa"))
    titulos = {secao.titulo for secao in modelo.secoes_preenchidas}
    for esperado in ("CLIENTE", "PRODUTO", "IMÓVEL", "ANÁLISE", "DECISÃO", "OPERAÇÃO", "METADADOS"):
        assert esperado in titulos, esperado
    assert any(tabela.titulo == "PARCELAS" for tabela in modelo.tabelas_preenchidas)


def test_pendencias_sao_declaradas_em_vez_de_omitidas():
    modelo = mapear_para_modelo(operacao_minima())
    texto = " ".join(modelo.pendencias)
    for processo_ausente in ("Score", "Decisão", "Juros", "Controle Financeiro"):
        assert processo_ausente in texto, processo_ausente

    completo = mapear_para_modelo(exemplo("operacao_completa"))
    assert completo.pendencias == ()


def test_mapeador_nao_calcula_valor_ausente():
    """Sem valorFinanciado no contrato, o documento nao pode exibir um."""
    operacao = exemplo("operacao_valida")
    del operacao["financiamento"]["imobiliario"]["valorFinanciado"]
    modelo = mapear_para_modelo(operacao)
    rotulos = {campo.rotulo for secao in modelo.secoes for campo in secao.campos}
    assert "Valor financiado" not in rotulos
    assert all(campo.rotulo != "Valor financiado" for campo in modelo.destaques)


def test_template_escolhido_por_produto():
    assert mapear_para_modelo(exemplo("operacao_valida")).chave_template == "proposta_imobiliaria"
    assert mapear_para_modelo(exemplo("operacao_credito_pj")).chave_template == TEMPLATE_PADRAO
    assert mapear_para_modelo(operacao_minima()).chave_template == TEMPLATE_PADRAO
    automotivo = com_bloco("financiamento", {"tipo": "AUTOMOTIVO", "automotivo": {}})
    assert mapear_para_modelo(automotivo).chave_template == TEMPLATE_PADRAO


def test_cronograma_vira_tabela_com_uma_linha_por_parcela():
    operacao = com_bloco("operacaoFinanceira", operacao_financeira_valida())
    tabela = mapear_para_modelo(operacao).tabelas_preenchidas[0]
    assert tabela.titulo == "PARCELAS"
    assert len(tabela.linhas) == 1
    assert len(tabela.colunas) == len(tabela.linhas[0])
    assert tabela.linhas[0][2] == "R$ 2.800,00"


def test_score_recebido_aparece_sem_ser_recalculado():
    operacao = com_bloco("score", score_valido())
    modelo = mapear_para_modelo(operacao)
    analise = next(secao for secao in modelo.secoes_preenchidas if secao.titulo == "ANÁLISE")
    valores = {campo.rotulo: campo.valor for campo in analise.campos}
    assert valores["Score final"] == "742"
    assert valores["Faixa de risco"] == "BOM"


def test_pessoa_juridica_e_apresentada_como_pj():
    modelo = mapear_para_modelo(exemplo("operacao_credito_pj"))
    cliente = next(secao for secao in modelo.secoes_preenchidas if secao.titulo == "CLIENTE")
    valores = {campo.rotulo: campo.valor for campo in cliente.campos}
    assert valores["Tipo de pessoa"] == "Pessoa jurídica"
    assert valores["Razão social"] == "Empresa Exemplo Ltda"
    assert "CPF" not in valores


# ---------------------------------------------------------------- templates

def test_templates_registrados():
    assert set(TEMPLATES) >= {"proposta_credito", "proposta_imobiliaria"}


def test_template_desconhecido_cai_no_padrao():
    """Produto novo sem template proprio ainda gera documento."""
    assert obter_template("produto_que_nao_existe") is TEMPLATES[TEMPLATE_PADRAO]
    assert obter_template(None) is TEMPLATES[TEMPLATE_PADRAO]


# ---------------------------------------------------------------------- PDF

def test_pdf_e_gerado_a_partir_do_modelo():
    with armazenamento_temporario() as diretorio:
        resultado = processo.executar_processo(exemplo("operacao_valida"))
        assert resultado["status"] == "sucesso"
        caminho = Path(resultado["documento"]["caminho_pdf"])
        assert caminho.exists()
        assert caminho.parent == diretorio / "pdfs"
        assert caminho.read_bytes().startswith(b"%PDF")
        assert caminho.stat().st_size > 1000


def test_pdf_de_cronograma_longo_usa_varias_paginas():
    with armazenamento_temporario():
        operacao = exemplo("operacao_completa")
        modelo_parcela = operacao["operacaoFinanceira"]["cronograma"][0]
        operacao["operacaoFinanceira"]["cronograma"] = [
            dict(modelo_parcela, numero=numero) for numero in range(1, 121)
        ]
        resultado = processo.executar_processo(operacao)
        assert resultado["status"] == "sucesso"
        conteudo = Path(resultado["documento"]["caminho_pdf"]).read_bytes()
        assert conteudo.count(b"/Type /Page\n") > 3 or conteudo.count(b"/Page") > 3


def test_nome_do_pdf_nao_escapa_da_pasta_de_armazenamento():
    """Identificador vindo de outro processo nao pode virar caminho de arquivo."""
    with armazenamento_temporario() as diretorio:
        operacao = operacao_minima()
        operacao["correlacao"]["idOperacao"] = "../../fora/OP-1"
        resultado = processo.executar_processo(operacao)
        assert resultado["status"] == "sucesso"
        caminho = Path(resultado["documento"]["caminho_pdf"]).resolve()
        assert caminho.parent == (diretorio / "pdfs").resolve()


# -------------------------------------------------------------- repositorio

def test_registro_guarda_os_metadados_exigidos():
    with armazenamento_temporario():
        resultado = processo.executar_processo(exemplo("operacao_valida"))
        registro = processo.buscar_documento(resultado["documento_id"])
        for campo in (
            "documento_id",
            "id_operacao",
            "criado_em",
            "tipo_documento",
            "versao_schema",
            "caminho_pdf",
            "status",
            "hash_documento",
        ):
            assert registro.get(campo), f"registro sem {campo}"
        assert registro["_id"] == registro["documento_id"]
        assert registro["status"] == "GERADO"
        assert registro["versao_schema"] == "1.2.0"
        assert registro["hash_documento"].startswith("sha256:")
        assert registro["correlacao"]["idOperacao"] == "OP-2026-000123"


def test_documento_inexistente_devolve_none():
    with armazenamento_temporario():
        assert processo.buscar_documento("nao-existe") is None


def test_consulta_nao_le_arquivo_fora_do_repositorio():
    import tempfile

    diretorio = tempfile.mkdtemp(prefix="esteira-repo-")
    repositorio = RepositorioArquivosJson(diretorio)
    assert repositorio.buscar("../../etc/passwd") is None
    assert repositorio.buscar("..") is None


def test_repositorio_grava_e_le_o_mesmo_registro():
    import tempfile

    diretorio = tempfile.mkdtemp(prefix="esteira-repo-")
    repositorio = RepositorioArquivosJson(diretorio)
    registro = RegistroDocumento(
        id_operacao="OP-1",
        tipo_documento="PROPOSTA_CREDITO",
        versao_schema="1.2.0",
        caminho_pdf="/tmp/x.pdf",
    )
    documento_id = repositorio.salvar(registro)
    lido = repositorio.buscar(documento_id)
    assert lido["documento_id"] == documento_id
    assert lido["id_operacao"] == "OP-1"


# ------------------------------------------------------------------ eventos

def test_evento_publicado_tem_formato_versionado():
    with armazenamento_temporario() as diretorio:
        resultado = processo.executar_processo(exemplo("operacao_valida"))
        evento = resultado["evento"]
        assert evento["eventType"] == "documento.gerado"
        assert evento["eventVersion"] == "1.0"
        assert evento["eventId"]
        assert evento["occurredAt"]
        assert evento["idOperacao"] == "OP-2026-000123"
        assert evento["documentoId"] == resultado["documento_id"]
        assert evento["tipoDocumento"] == "PROPOSTA_CREDITO"
        assert evento["schemaVersion"] == "1.2.0"
        assert evento["referencia"]["caminhoPdf"]
        assert evento["referencia"]["hashDocumento"].startswith("sha256:")
        arquivos = list((diretorio / "eventos").glob("*.json"))
        assert len(arquivos) == 1


def test_evento_mantem_os_campos_da_versao_1_0_0():
    with armazenamento_temporario():
        evento = processo.executar_processo(exemplo("operacao_valida"))["evento"]
        assert evento["evento"] == "documento.gerado"
        assert evento["documento_id"] == evento["documentoId"]
        assert evento["id_operacao"] == evento["idOperacao"]
        assert evento["caminho_pdf"] == evento["referencia"]["caminhoPdf"]
        assert evento["publicado_em"] == evento["occurredAt"]


def test_publicador_grava_um_arquivo_por_evento():
    import tempfile

    diretorio = tempfile.mkdtemp(prefix="esteira-evt-")
    publicador = PublicadorArquivoJson(diretorio)
    mensagem = publicador.publicar(
        EventoDocumento(
            documento_id="doc-1",
            id_operacao="OP-1",
            tipo_documento="PROPOSTA_CREDITO",
            versao_schema="1.2.0",
            caminho_pdf="/tmp/x.pdf",
        )
    )
    assert mensagem["eventType"] == "documento.gerado"
    assert (Path(diretorio) / "doc-1.json").exists()


# ------------------------------------------------------- fluxo do processo

def test_entrada_invalida_nao_gera_pdf_registro_nem_evento():
    """A regra central do gateway 'Dados validos?' do BPMN."""
    with armazenamento_temporario() as diretorio:
        resultado = processo.executar_processo(exemplo("operacao_invalida"))
        assert resultado["status"] == "erro"
        assert resultado["codigo"] == "DADOS_INVALIDOS"
        assert resultado["detalhes"]
        assert not (diretorio / "pdfs").exists()
        assert not (diretorio / "documentos").exists()
        assert not (diretorio / "eventos").exists()


def test_erro_informa_o_formato_e_a_versao_do_contrato():
    with armazenamento_temporario():
        resultado = processo.executar_processo(exemplo("operacao_invalida"))
        assert resultado["formatoEntrada"] == "canonico"
        assert resultado["versaoContrato"] == "1.2.0"
        assert resultado["erros"][0]["campo"]


def test_formato_legado_e_identificado_na_resposta():
    with armazenamento_temporario():
        resultado = processo.executar_processo(exemplo("legado_v1_plano"))
        assert resultado["status"] == "sucesso"
        assert resultado["formatoEntrada"] == "legado_v1"


def test_todos_os_exemplos_validos_geram_documento():
    with armazenamento_temporario():
        for nome in (
            "operacao_valida",
            "operacao_com_score",
            "operacao_com_decisao",
            "operacao_completa",
            "operacao_credito_pj",
            "legado_v1_plano",
        ):
            resultado = processo.executar_processo(exemplo(nome))
            assert resultado["status"] == "sucesso", (nome, resultado.get("detalhes"))
            assert Path(resultado["documento"]["caminho_pdf"]).exists()


def test_documentos_diferentes_recebem_identificadores_diferentes():
    with armazenamento_temporario():
        primeiro = processo.executar_processo(exemplo("operacao_valida"))
        segundo = processo.executar_processo(exemplo("operacao_valida"))
        assert primeiro["documento_id"] != segundo["documento_id"]
        assert processo.buscar_documento(primeiro["documento_id"]) is not None
        assert processo.buscar_documento(segundo["documento_id"]) is not None


def test_corpo_que_nao_e_objeto_e_recusado_sem_quebrar():
    with armazenamento_temporario():
        for corpo in ([], "texto", 10, None):
            resultado = processo.executar_processo(corpo)
            assert resultado["status"] == "erro"
            assert resultado["codigo"] == "DADOS_INVALIDOS"
