"""Mascaramento para exibição em PDF; não modifica os dados recebidos."""
import re

def mascarar_documento(valor):
    if valor is None:
        return "Não informado"
    digitos = re.sub(r"\D", "", str(valor))
    if len(digitos) == 11:
        return f"***.{digitos[3:6]}.{digitos[6:9]}-**"
    if len(digitos) == 14:
        return f"**.{digitos[2:5]}.{digitos[5:8]}/****-**"
    return "***"
