from __future__ import annotations


def mapear_para_template(operacao: dict) -> dict:
    valor = operacao["valor"]
    taxa = operacao["taxa_juros_mensal"]
    return {
        "titulo": "Proposta de Operação de Crédito",
        "id_operacao": operacao["id_operacao"],
        "tipo_produto": operacao["tipo_produto"].replace("_", " ").title(),
        "nome_cliente": operacao["cliente"]["nome"],
        "documento_cliente": operacao["cliente"]["documento"],
        "valor_formatado": f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "prazo_meses": operacao["prazo_meses"],
        "taxa_formatada": f"{taxa:.2f}% ao mês",
    }
