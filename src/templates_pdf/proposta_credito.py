"""Template generico da proposta de operacao de credito.

Usado quando o produto da operacao nao tem template proprio - hoje credito
pessoal, financiamento automotivo e qualquer operacao que chegue sem o bloco de
financiamento. Apresenta as secoes na ordem do modelo documental, sem nenhum
tratamento especifico de produto.

Serve tambem de ponto de partida para um template novo: copie este arquivo,
mude o que o produto pede e registre a chave em ``templates_pdf/__init__.py``.
"""
from __future__ import annotations

from ..modelo_documental import ModeloDocumental
from . import base

#: Aparece na chave do template e na documentacao.
CHAVE = "proposta_credito"
DESCRICAO = "Proposta de crédito — layout padrão, sem tratamento por produto."


def montar(modelo: ModeloDocumental) -> list:
    """Devolve os elementos do documento na ordem em que serao impressos."""
    return base.documento_completo(modelo, base.estilos())
