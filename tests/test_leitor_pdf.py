"""Testes do leitor de PDF (src/leitor_pdf.py).

Os PDFs lidos aqui sao emitidos pelo proprio processo, o que fecha o ciclo
JSON -> PDF -> texto: o que entrou no JSON tem de sair legivel no documento.
"""
from __future__ import annotations

from src import processo
from src.leitor_pdf import ErroLeituraPdf, conferir_integridade, ler_pdf
from tests.apoio import armazenamento_temporario, exemplo


def _emitir(nome_exemplo: str) -> dict:
    resultado = processo.executar_processo(exemplo(nome_exemplo))
    assert resultado["status"] == "sucesso"
    return resultado["documento"]


def test_le_texto_do_pdf_emitido():
    with armazenamento_temporario():
        documento = _emitir("operacao_completa")
        conteudo = ler_pdf(documento["caminho_pdf"])

    assert conteudo.numero_paginas >= 1
    assert conteudo.contem("Cliente Exemplo Contratado")
    assert conteudo.contem("123.456.789-04")
    assert conteudo.contem(documento["id_operacao"])


def test_le_metadados_gravados_na_emissao():
    with armazenamento_temporario():
        documento = _emitir("operacao_completa")
        conteudo = ler_pdf(documento["caminho_pdf"])

    assert conteudo.metadados["assunto"] == documento["tipo_documento"]
    assert conteudo.metadados["titulo"]
    assert "Estruturação de Documentos" in conteudo.metadados["autor"]


def test_hash_da_leitura_bate_com_o_registro():
    with armazenamento_temporario():
        documento = _emitir("operacao_valida")
        conteudo = ler_pdf(documento["caminho_pdf"])
        intacto = conferir_integridade(documento["caminho_pdf"], documento["hash_documento"])

    assert conteudo.hash_documento == documento["hash_documento"]
    assert intacto


def test_pdf_alterado_falha_na_conferencia_de_integridade():
    with armazenamento_temporario():
        documento = _emitir("operacao_valida")
        with open(documento["caminho_pdf"], "ab") as arquivo:
            arquivo.write(b"\n% alterado depois da emissao\n")
        intacto = conferir_integridade(documento["caminho_pdf"], documento["hash_documento"])

    assert not intacto


def test_como_dict_traz_paginas_e_metadados():
    with armazenamento_temporario():
        documento = _emitir("operacao_valida")
        dados = ler_pdf(documento["caminho_pdf"]).como_dict()

    assert dados["numero_paginas"] == len(dados["paginas"])
    assert dados["hash_documento"].startswith("sha256:")
    assert "metadados" in dados


def test_arquivo_inexistente_e_recusado(tmp_path):
    try:
        ler_pdf(tmp_path / "nao_existe.pdf")
    except ErroLeituraPdf as erro:
        assert "não encontrado" in str(erro)
    else:
        raise AssertionError("deveria recusar arquivo inexistente")


def test_arquivo_que_nao_e_pdf_e_recusado(tmp_path):
    falso = tmp_path / "falso.pdf"
    falso.write_text('{"isto": "e um json"}', encoding="utf-8")
    try:
        ler_pdf(falso)
    except ErroLeituraPdf as erro:
        assert "não é um PDF" in str(erro)
    else:
        raise AssertionError("deveria recusar arquivo que nao e PDF")


def test_pdf_corrompido_e_recusado(tmp_path):
    corrompido = tmp_path / "corrompido.pdf"
    corrompido.write_bytes(b"%PDF-1.4\nconteudo quebrado sem estrutura")
    try:
        ler_pdf(corrompido)
    except ErroLeituraPdf:
        pass
    else:
        raise AssertionError("deveria recusar PDF corrompido")
