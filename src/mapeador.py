"""Tarefa BPMN: "Mapear dados" (operação validada -> dicionário pronto para o template)."""
from __future__ import annotations
from datetime import datetime
from .privacidade import mascarar_documento

NOMES_PRODUTO = {
    "financiamento_imovel": "Financiamento de Imóvel",
    "financiamento_automovel": "Financiamento de Automóvel",
    "credito_pessoal": "Crédito Pessoal",
}


def formatar_moeda(valor: float) -> str:
    texto = f"{valor:,.2f}"  # 45,000.00
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_percentual(taxa: float) -> str:
    return f"{taxa:.2f}".replace(".", ",") + "% ao mês"


def mapear_para_template(operacao: dict, emitido_em: datetime) -> dict:
    return {
        "titulo": "Proposta de Operação de Crédito",
        "id_operacao": operacao["id_operacao"],
        "tipo_produto": NOMES_PRODUTO.get(operacao["tipo_produto"], operacao["tipo_produto"]),
        "nome_cliente": operacao["cliente"]["nome"],
        "documento_cliente": mascarar_documento(operacao["cliente"]["documento"]),
        "valor_formatado": formatar_moeda(operacao["valor"]),
        "prazo_meses": operacao["prazo_meses"],
        "taxa_formatada": formatar_percentual(operacao["taxa_juros_mensal"]),
        "emitido_em": emitido_em.strftime("%d/%m/%Y %H:%M UTC"),
    }
