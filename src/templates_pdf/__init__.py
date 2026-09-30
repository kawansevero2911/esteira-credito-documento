"""Registro de templates de PDF.

Um template e uma funcao que recebe o modelo documental e devolve os elementos
do PDF. Cada produto financeiro pode ter o seu, e a escolha acontece por uma
CHAVE decidida pelo mapeador - nao por ``if`` espalhado no gerador.

Para acrescentar um produto:

1. crie ``templates_pdf/<produto>.py`` com ``CHAVE``, ``DESCRICAO`` e ``montar``;
2. registre-o em ``TEMPLATES``, abaixo;
3. ligue o produto a chave em ``mapeador.TEMPLATES_POR_PRODUTO``.

Nenhum outro arquivo precisa mudar. Produtos cujos dados ainda nao foram
definidos pelos grupos responsaveis (credito PJ, automotivo) usam o template
generico ate que o contrato exista - deliberadamente, para nao inventar
layout para dado que nao chegou.
"""
from __future__ import annotations

from collections.abc import Callable

from ..modelo_documental import TEMPLATE_PADRAO, ModeloDocumental
from . import proposta_credito, proposta_imobiliaria

Montador = Callable[[ModeloDocumental], list]

TEMPLATES: dict[str, Montador] = {
    proposta_credito.CHAVE: proposta_credito.montar,
    proposta_imobiliaria.CHAVE: proposta_imobiliaria.montar,
}

DESCRICOES: dict[str, str] = {
    proposta_credito.CHAVE: proposta_credito.DESCRICAO,
    proposta_imobiliaria.CHAVE: proposta_imobiliaria.DESCRICAO,
}


def registrar_template(chave: str, montador: Montador, descricao: str = "") -> None:
    """Registra um template novo em tempo de execucao."""
    TEMPLATES[chave] = montador
    DESCRICOES[chave] = descricao


def obter_template(chave: str | None) -> Montador:
    """Devolve o montador da chave, caindo no template generico se nao existir.

    A queda para o generico e intencional: um produto novo que ainda nao tenha
    template continua gerando documento, em vez de derrubar o fluxo.
    """
    if chave and chave in TEMPLATES:
        return TEMPLATES[chave]
    return TEMPLATES[TEMPLATE_PADRAO]


__all__ = [
    "DESCRICOES",
    "TEMPLATES",
    "Montador",
    "obter_template",
    "registrar_template",
]
