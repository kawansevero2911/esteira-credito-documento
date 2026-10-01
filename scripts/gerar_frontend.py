"""Regera web/index.html com os exemplos de examples/ embutidos.

Uso (na raiz do projeto):
    python -m scripts.gerar_frontend

O banco de provas e um arquivo unico, que precisa funcionar aberto direto do
disco. Por isso os exemplos ficam EMBUTIDOS nele, em vez de buscados por
fetch: o protocolo file:// nao le arquivos vizinhos.

Embutir cria um risco: o arquivo envelhecer em relacao a examples/. Este
script resolve isso - os exemplos sao copiados dos arquivos reais, e o teste
tests/test_frontend.py falha quando o que esta embutido difere do que esta em
examples/, do mesmo modo que o contrato consolidado e conferido contra os
modulos de schemas/v1/.

Rode este comando sempre que alterar qualquer arquivo de examples/.

O molde da pagina fica em web/modelo.html, com o marcador
/*__EXEMPLOS__*/ no lugar onde os exemplos entram.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DIR_EXEMPLOS = BASE_DIR / "examples"
MOLDE = BASE_DIR / "web" / "modelo.html"
DESTINO = BASE_DIR / "web" / "index.html"

MARCADOR = "/*__EXEMPLOS__*/"

#: Casos na ordem em que aparecem na tela, com o rotulo, a explicacao e o
#: codigo HTTP esperado. Os rotulos espelham EXEMPLOS_OPERACAO de src/api.py
#: para que o Swagger e o banco de provas contem a mesma historia.
CENARIOS: list[tuple[str, str, str, int]] = [
    (
        "operacao_valida",
        "Financiamento imobiliário PF",
        "Enviada pelo processo Financiamento de Imóveis, sem score, decisão nem operação financeira.",
        201,
    ),
    (
        "operacao_com_score",
        "Com score",
        "A mesma operação, acrescida do bloco score preenchido pelo processo Score.",
        201,
    ),
    (
        "operacao_com_decisao",
        "Com decisão e juros",
        "Acrescenta os blocos juros e decisao.",
        201,
    ),
    (
        "operacao_completa",
        "Com operação financeira e cronograma",
        "Percorre a Esteira inteira, com o cronograma de parcelas do Controle Financeiro.",
        201,
    ),
    (
        "operacao_credito_pj",
        "Crédito pessoa jurídica",
        "O contrato não é exclusivo de pessoa física. dadosPJ não exige campos: depende do grupo Crédito PF e PJ.",
        201,
    ),
    (
        "legado_v1_plano",
        "Formato plano da v1.0.0",
        "Formato antigo, em snake_case. É convertido para o contrato canônico antes da validação.",
        201,
    ),
    (
        "operacao_invalida",
        "Operação inválida",
        "CPF com pontuação, data inexistente, valor negativo, prazo zero, enums inválidos e score fora de 0–1000.",
        400,
    ),
]


def montar_exemplos() -> dict[str, dict]:
    """Le examples/ e monta o objeto que a pagina recebe."""
    exemplos: dict[str, dict] = {}
    for chave, rotulo, descricao, esperado in CENARIOS:
        caminho = DIR_EXEMPLOS / f"{chave}.json"
        if not caminho.exists():
            raise FileNotFoundError(f"Exemplo nao encontrado: {caminho}")
        exemplos[chave] = {
            "rotulo": rotulo,
            "descricao": descricao,
            "esperado": esperado,
            "dados": json.loads(caminho.read_text(encoding="utf-8")),
        }
    return exemplos


def construir_pagina() -> str:
    """Devolve o HTML do banco de provas, com os exemplos embutidos."""
    molde = MOLDE.read_text(encoding="utf-8")
    if MARCADOR not in molde:
        raise ValueError(f"O molde {MOLDE} nao contem o marcador {MARCADOR}")
    exemplos = json.dumps(montar_exemplos(), ensure_ascii=False, indent=2)
    return molde.replace(MARCADOR, exemplos)


def main() -> None:
    DESTINO.write_text(construir_pagina(), encoding="utf-8")
    print(f"Banco de provas gerado em {DESTINO}")


if __name__ == "__main__":
    main()
