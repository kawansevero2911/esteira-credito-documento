"""Testes da extracao e formatacao de informacoes de PDF (src/extrator_pdf.py).

Dois tipos de PDF sao cobertos: o emitido por este processo (rotulo numa linha
e valor na seguinte, com tabela no cabecalho) e uma ficha "livre", no formato
``Rotulo: valor``, como a que um cliente ou outro sistema mandaria.
"""
from __future__ import annotations

from reportlab.pdfgen import canvas

from src import processo
from src.extrator_pdf import (
    cnpj_valido,
    cpf_valido,
    extrair_informacoes,
    ler_e_formatar,
    normalizar_data,
    normalizar_dinheiro,
    normalizar_percentual,
)
from tests.apoio import armazenamento_temporario, exemplo

FICHA = [
    "FICHA CADASTRAL",
    "Nome completo: MARIA DAS GRACAS SOUZA",
    "CPF: 529.982.247-25",
    "Data de nascimento: 03/02/1990",
    "E-mail: Maria.Souza@Exemplo.com",
    "Celular: (11) 98765-4321",
    "Endereço: Rua das Flores, 100 - Campinas/SP",
    "CEP: 13010-000",
    "Renda mensal: R$ 7.850,00",
    "Valor solicitado: R$ 25.000",
    "Prazo: 36 meses",
    "Taxa de juros: 2,1% a.m.",
]


def _ficha_em_pdf(pasta) -> str:
    caminho = str(pasta / "ficha.pdf")
    pdf = canvas.Canvas(caminho)
    for i, linha in enumerate(FICHA):
        pdf.drawString(50, 800 - 20 * i, linha)
    pdf.save()
    return caminho


# --------------------------------------------------------------- ficha livre

def test_ficha_livre_tem_campos_normalizados_e_formatados(tmp_path):
    dados = ler_e_formatar(_ficha_em_pdf(tmp_path))["informacoes"]["dados"]

    assert dados["nome"]["formatado"] == "Maria das Gracas Souza"
    assert dados["cpf"] == {
        "valor": "52998224725", "formatado": "529.982.247-25", "valido": True, "rotulo": "CPF",
    }
    assert dados["data_nascimento"]["valor"] == "1990-02-03"
    assert dados["email"]["valor"] == "maria.souza@exemplo.com"
    assert dados["telefone"]["formatado"] == "(11) 98765-4321"
    assert dados["cep"]["formatado"] == "13010-000"
    assert dados["renda_mensal"]["valor"] == 7850.0
    assert dados["valor_solicitado"]["formatado"] == "R$ 25.000,00"
    assert dados["prazo_meses"]["valor"] == 36
    assert dados["taxa_juros"]["formatado"] == "2,1% ao mês"


def test_ficha_livre_vira_bloco_cliente_do_contrato(tmp_path):
    cliente = ler_e_formatar(_ficha_em_pdf(tmp_path))["informacoes"]["cliente"]

    assert cliente["tipoPessoa"] == "PF"
    assert cliente["dadosPF"] == {
        "nomeCompleto": "Maria das Gracas Souza",
        "cpf": "52998224725",
        "dataNascimento": "1990-02-03",
    }
    assert cliente["contato"]["telefone"] == "11987654321"


# ------------------------------------------------------- PDF deste processo

def test_pdf_emitido_volta_com_os_dados_da_operacao():
    with armazenamento_temporario():
        resultado = processo.executar_processo(exemplo("operacao_completa"))
        dados = ler_e_formatar(resultado["documento"]["caminho_pdf"])["informacoes"]["dados"]

    # Cabecalho em tabela: rotulos numa linha, valores na de baixo.
    assert dados["valor_imovel"]["formatado"] == "R$ 500.000,00"
    assert dados["valor_entrada"]["formatado"] == "R$ 180.000,00"
    assert dados["valor_financiado"]["formatado"] == "R$ 320.000,00"
    assert dados["prazo_meses"]["valor"] == 240
    assert dados["sistema_amortizacao"]["valor"] == "PRICE"
    # Secao do cliente: rotulo numa linha, valor na seguinte.
    assert dados["nome"]["valor"] == "Cliente Exemplo Contratado"
    assert dados["cpf"]["valor"] == "12345678904"
    assert dados["email"]["valor"] == "cliente.contratado@example.com"


def test_pdf_de_pessoa_juridica_vira_cliente_pj():
    with armazenamento_temporario():
        resultado = processo.executar_processo(exemplo("operacao_credito_pj"))
        cliente = ler_e_formatar(resultado["documento"]["caminho_pdf"])["informacoes"]["cliente"]

    assert cliente["tipoPessoa"] == "PJ"
    assert cliente["dadosPJ"]["cnpj"] == "12345678000199"


# ------------------------------------------------------------ regras soltas

def test_valor_fora_do_formato_e_descartado():
    """O rotulo casou com texto errado: melhor sem o campo do que com lixo."""
    dados = extrair_informacoes("CPF: nao informado\nValor da parcela\nJuros")["dados"]
    assert "cpf" not in dados
    assert "valor_parcela" not in dados


def test_encontra_dados_sem_rotulo():
    texto = "Contato maria@x.com ou (21) 3333-4444, CNPJ 11.222.333/0001-81, R$ 1.500,50 em 10/05/2026"
    achados = extrair_informacoes(texto)["encontrados"]
    assert achados["email"] == ["maria@x.com"]
    assert achados["telefone"] == ["(21) 3333-4444"]
    assert achados["cnpj"][0]["valido"] is True
    assert "cpf" not in achados  # o CNPJ nao pode ser lido como CPF
    assert achados["dinheiro"][0]["valor"] == 1500.5
    assert achados["data"][0]["valor"] == "2026-05-10"


def test_validacao_de_cpf_e_cnpj():
    assert cpf_valido("529.982.247-25")
    assert not cpf_valido("123.456.789-00")
    assert not cpf_valido("111.111.111-11")
    assert cnpj_valido("11.222.333/0001-81")
    assert not cnpj_valido("11.222.333/0001-00")


def test_normalizacoes():
    assert normalizar_dinheiro("R$ 1.234,56") == 1234.56
    assert normalizar_dinheiro("R$ 25.000") == 25000.0
    assert normalizar_data("31/12/2025") == "2025-12-31"
    assert normalizar_data("31/02/2025") is None  # data que nao existe
    assert normalizar_percentual("12% ao ano")["periodo"] == "ano"
    assert normalizar_percentual("1,99% ao mês")["valor"] == 1.99


def test_pdf_sem_texto_avisa_que_precisa_de_ocr(tmp_path):
    caminho = str(tmp_path / "vazio.pdf")
    pdf = canvas.Canvas(caminho)
    pdf.rect(50, 50, 100, 100)  # so desenho, nenhum texto
    pdf.save()
    resultado = ler_e_formatar(caminho)
    assert resultado["aviso_texto_vazio"]
