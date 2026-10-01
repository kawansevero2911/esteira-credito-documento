"""Testes do banco de provas de web/.

O arquivo web/index.html e GERADO a partir de web/modelo.html, com os exemplos
de examples/ embutidos. Embutir e necessario porque a pagina tem de funcionar
aberta direto do disco, onde fetch de arquivo vizinho nao funciona - mas cria o
risco de a pagina envelhecer em relacao aos exemplos reais.

Estes testes fecham esse risco, do mesmo modo que test_contrato.py confere o
contrato consolidado contra os modulos de schemas/v1/.
"""
from __future__ import annotations

import json
import re

from scripts.gerar_frontend import CENARIOS, DESTINO, MARCADOR, MOLDE, construir_pagina
from tests.apoio import exemplo

PAGINA = DESTINO.read_text(encoding="utf-8")


def exemplos_embutidos() -> dict:
    """Le o objeto EXEMPLOS de dentro do HTML gerado."""
    achado = re.search(r"const EXEMPLOS = (\{.*?\n\});", PAGINA, re.S)
    assert achado, "web/index.html nao declara const EXEMPLOS"
    return json.loads(achado.group(1))


# ------------------------------------------------------------- sincronia

def test_pagina_gerada_esta_sincronizada_com_o_molde_e_os_exemplos():
    """Falha quando alguem edita examples/ ou o molde e esquece de regerar.

    Corrija com: python -m scripts.gerar_frontend
    """
    assert PAGINA == construir_pagina()


def test_marcador_do_molde_foi_resolvido():
    assert MARCADOR in MOLDE.read_text(encoding="utf-8")
    assert MARCADOR not in PAGINA


def test_exemplos_embutidos_sao_identicos_aos_de_examples():
    embutidos = exemplos_embutidos()
    for chave, _rotulo, _descricao, _esperado in CENARIOS:
        assert embutidos[chave]["dados"] == exemplo(chave), chave


def test_todos_os_exemplos_do_repositorio_estao_na_tela():
    """Nenhum cenario de examples/ pode ficar de fora do banco de provas."""
    from tests.apoio import EXEMPLOS as DIR_EXEMPLOS

    no_disco = {caminho.stem for caminho in DIR_EXEMPLOS.glob("*.json")}
    na_tela = {chave for chave, *_ in CENARIOS}
    assert na_tela == no_disco


# ------------------------------------------------------------- conteudo

def test_cada_caso_declara_rotulo_descricao_e_codigo_esperado():
    for chave, caso in exemplos_embutidos().items():
        assert caso["rotulo"], chave
        assert caso["descricao"], chave
        assert caso["esperado"] in (201, 400), chave


def test_o_caso_invalido_espera_400_e_os_demais_201():
    embutidos = exemplos_embutidos()
    assert embutidos["operacao_invalida"]["esperado"] == 400
    for chave, caso in embutidos.items():
        if chave != "operacao_invalida":
            assert caso["esperado"] == 201, chave


def test_pagina_cobre_os_tres_endpoints():
    for caminho in ("/api/saude", "/api/documentos"):
        assert caminho in PAGINA, caminho
    assert "/api/documentos/" in PAGINA


def test_pagina_nao_depende_de_build_nem_de_framework():
    """Arquivo unico: nada de import de modulo, bundler ou CDN de framework."""
    assert "<script" in PAGINA
    for proibido in ("require(", "from 'react'", 'from "react"', "vue.js", "jquery"):
        assert proibido not in PAGINA, proibido


def test_pagina_declara_idioma_e_viewport():
    assert 'lang="pt-BR"' in PAGINA
    assert 'name="viewport"' in PAGINA
