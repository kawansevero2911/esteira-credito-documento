"""Extracao e formatacao das informacoes de um PDF recebido.

O ``leitor_pdf`` devolve o texto cru. Este modulo transforma esse texto em
dados organizados, em duas camadas:

1. ``dados``: campos encontrados pelo ROTULO (``Nome``, ``CPF``, ``Valor
   financiado``...), tanto no formato ``Rotulo: valor`` na mesma linha quanto
   no formato rotulo numa linha e valor na seguinte (o layout dos PDFs deste
   projeto). Cada campo vem com o valor normalizado (CPF so com digitos, data
   em ISO, dinheiro como numero) e com o valor formatado para leitura.
2. ``encontrados``: tudo o que tem formato reconhecivel no texto, mesmo sem
   rotulo - CPFs, CNPJs, e-mails, telefones, CEPs, datas, valores em reais e
   percentuais.

Por fim, ``cliente`` junta o que foi achado nos nomes do contrato canonico
(``nomeCompleto``, ``cpf``, ``dataNascimento``...), para facilitar montar uma
operacao a partir do PDF.

A extracao e por padroes de texto, nao por IA: funciona bem com PDFs gerados
por sistema e com rotulos usuais; um PDF com layout muito livre pode trazer
campos a menos. Por isso o texto completo tambem volta na resposta.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

from .leitor_pdf import ConteudoPdf, ler_pdf
from .mapeador import formatar_cnpj, formatar_cpf, formatar_data, formatar_moeda

# ------------------------------------------------------------------ rotulos

#: Rotulo (sem acento, minusculo) -> chave do campo.
ROTULOS: dict[str, str] = {
    "nome": "nome",
    "nome completo": "nome",
    "nome do cliente": "nome",
    "razao social": "razao_social",
    "nome fantasia": "nome_fantasia",
    "cpf": "cpf",
    "cnpj": "cnpj",
    "data de nascimento": "data_nascimento",
    "nascimento": "data_nascimento",
    "e-mail": "email",
    "email": "email",
    "telefone": "telefone",
    "celular": "telefone",
    "endereco": "endereco",
    "cep": "cep",
    "estado civil": "estado_civil",
    "profissao": "profissao",
    "renda": "renda_mensal",
    "renda mensal": "renda_mensal",
    "valor do imovel": "valor_imovel",
    "valor do veiculo": "valor_veiculo",
    "valor do bem": "valor_bem",
    "entrada": "valor_entrada",
    "valor de entrada": "valor_entrada",
    "valor financiado": "valor_financiado",
    "valor solicitado": "valor_solicitado",
    "valor do emprestimo": "valor_solicitado",
    "valor da parcela": "valor_parcela",
    "parcela": "valor_parcela",
    "prazo": "prazo_meses",
    "taxa de juros": "taxa_juros",
    "amortizacao": "sistema_amortizacao",
    "score": "score",
}

#: Campos com formato fixo: se o valor achado nao tiver o formato, o par e
#: descartado (provavelmente o rotulo casou com o texto errado) e vale a
#: proxima ocorrencia do mesmo rotulo.
_CAMPOS_COM_FORMATO = {
    "cpf", "cnpj", "data_nascimento", "email", "telefone", "cep", "prazo_meses", "taxa_juros",
}

_CAMPOS_DINHEIRO = {
    "renda_mensal", "valor_imovel", "valor_veiculo", "valor_bem", "valor_entrada",
    "valor_financiado", "valor_solicitado", "valor_parcela",
}

# ------------------------------------------------------------------ padroes

_RE_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
_RE_CNPJ = re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
_RE_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_RE_TELEFONE = re.compile(r"\(\d{2}\)\s?9?\d{4}-?\d{4}")
_RE_CEP = re.compile(r"(?<!\d)\d{5}-\d{3}(?!\d)")
_RE_DATA_BR = re.compile(r"(?<!\d)(\d{2})/(\d{2})/(\d{4})(?!\d)")
_RE_DATA_ISO = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
_RE_DINHEIRO = re.compile(r"R\$\s?-?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|R\$\s?-?\d+(?:,\d{1,2})?")
_RE_PERCENTUAL = re.compile(
    r"-?\d+(?:[.,]\d+)?\s?%(?:\s?(?:a\.\s?m\.?|a\.\s?a\.?|ao\s(?:m[eê]s|ano)))?", re.I
)


def _sem_acento(texto: str) -> str:
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in normalizado if not unicodedata.combining(c))


def _chave_do_rotulo(rotulo: str) -> str | None:
    limpo = _sem_acento(rotulo).lower().strip(" :.-\t")
    return ROTULOS.get(" ".join(limpo.split()))


def _digitos(texto: str) -> str:
    return re.sub(r"\D", "", texto)


# --------------------------------------------------------------- validacoes

def cpf_valido(cpf: str) -> bool:
    """Confere os digitos verificadores do CPF."""
    cpf = _digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(cpf[i]) * (posicao + 1 - i) for i in range(posicao))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[posicao]):
            return False
    return True


def cnpj_valido(cnpj: str) -> bool:
    """Confere os digitos verificadores do CNPJ."""
    cnpj = _digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    for tamanho in (12, 13):
        # 1o digito usa os pesos 5..2,9..2; o 2o usa 6..2,9..2.
        pesos_digito = pesos[13 - tamanho :]
        soma = sum(int(cnpj[i]) * pesos_digito[i] for i in range(tamanho))
        resto = soma % 11
        digito = 0 if resto < 2 else 11 - resto
        if digito != int(cnpj[tamanho]):
            return False
    return True


# ---------------------------------------------------------- normalizacoes

def normalizar_dinheiro(texto: str) -> float | None:
    """``R$ 1.234,56`` -> ``1234.56``."""
    numero = re.sub(r"[^\d,.-]", "", texto)
    if not numero:
        return None
    if "," in numero:
        numero = numero.replace(".", "").replace(",", ".")
    elif numero.count(".") > 1 or re.fullmatch(r"-?\d{1,3}(\.\d{3})+", numero):
        numero = numero.replace(".", "")
    try:
        return float(numero)
    except ValueError:
        return None


def normalizar_data(texto: str) -> str | None:
    """``15/07/1982`` ou ``1982-07-15`` -> ``1982-07-15``; None se nao for data real."""
    achado = _RE_DATA_BR.search(texto)
    if achado:
        dia, mes, ano = achado.groups()
    else:
        achado = _RE_DATA_ISO.search(texto)
        if not achado:
            return None
        ano, mes, dia = achado.groups()
    try:
        return date(int(ano), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


def normalizar_percentual(texto: str) -> dict[str, Any] | None:
    """``2,1% a.m.`` -> ``{"valor": 2.1, "periodo": "mes", "formatado": "2,1% ao mês"}``.

    ``valor`` fica em PERCENTUAL (2.1 = 2,1%), nao em decimal (0.021).
    """
    achado = re.search(r"(-?\d+(?:[.,]\d+)?)\s?%", texto)
    if not achado:
        return None
    valor = float(achado.group(1).replace(",", "."))
    resto = _sem_acento(texto[achado.end():]).lower()
    periodo = "ano" if re.match(r"\s*(a\.\s?a|ao\s+ano)", resto) else (
        "mes" if re.match(r"\s*(a\.\s?m|ao\s+mes)", resto) else None
    )
    numero = f"{valor:.4f}".rstrip("0").rstrip(".").replace(".", ",")
    sufixo = {"mes": " ao mês", "ano": " ao ano"}.get(periodo, "")
    return {"valor": valor, "periodo": periodo, "formatado": f"{numero}%{sufixo}"}


def formatar_telefone(texto: str) -> str | None:
    numeros = _digitos(texto)
    if numeros.startswith("55") and len(numeros) in (12, 13):
        numeros = numeros[2:]
    if len(numeros) == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    if len(numeros) == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"
    return None


def formatar_cep(texto: str) -> str | None:
    numeros = _digitos(texto)
    return f"{numeros[:5]}-{numeros[5:]}" if len(numeros) == 8 else None


def _normalizar_campo(chave: str, bruto: str) -> dict[str, Any] | None:
    """Valor normalizado (para sistema) e formatado (para leitura) de um campo.

    Devolve None quando um campo de formato fixo (CPF, data, dinheiro...) nao
    tem esse formato.
    """
    bruto = " ".join(bruto.split())
    campo: dict[str, Any] = {"valor": bruto, "formatado": bruto}
    original = dict(campo)

    if chave == "cpf":
        numeros = _digitos(bruto)
        if len(numeros) == 11:
            campo.update(valor=numeros, formatado=formatar_cpf(numeros), valido=cpf_valido(numeros))
    elif chave == "cnpj":
        numeros = _digitos(bruto)
        if len(numeros) == 14:
            campo.update(valor=numeros, formatado=formatar_cnpj(numeros), valido=cnpj_valido(numeros))
    elif chave == "data_nascimento":
        iso = normalizar_data(bruto)
        if iso:
            campo.update(valor=iso, formatado=formatar_data(iso))
    elif chave == "telefone":
        formatado = formatar_telefone(bruto)
        if formatado:
            campo.update(valor=_digitos(formatado), formatado=formatado)
    elif chave == "cep":
        formatado = formatar_cep(bruto)
        if formatado:
            campo.update(valor=_digitos(formatado), formatado=formatado)
    elif chave == "email":
        achado = _RE_EMAIL.search(bruto)
        if not achado:
            return None
        email = achado.group(0).lower()
        return {"valor": email, "formatado": email}
    elif chave in _CAMPOS_DINHEIRO:
        numero = normalizar_dinheiro(bruto)
        if numero is not None:
            campo.update(valor=numero, formatado=formatar_moeda(numero))
    elif chave == "prazo_meses":
        achado = re.search(r"\d+", bruto)
        if achado:
            meses = int(achado.group(0))
            campo.update(valor=meses, formatado=f"{meses} {'mês' if meses == 1 else 'meses'}")
    elif chave == "taxa_juros":
        taxa = normalizar_percentual(bruto)
        if taxa:
            campo.update(taxa)
    elif chave == "nome" or chave == "razao_social":
        if bruto.isupper() or bruto.islower():
            campo["formatado"] = _nome_proprio(bruto)
    formato_fixo = chave in _CAMPOS_COM_FORMATO or chave in _CAMPOS_DINHEIRO
    if formato_fixo and campo == original:
        return None
    return campo


_PARTICULAS = {"da", "de", "do", "das", "dos", "e"}


def _nome_proprio(nome: str) -> str:
    """``MARIA DA SILVA`` -> ``Maria da Silva``."""
    palavras = nome.lower().split()
    return " ".join(
        p if (p in _PARTICULAS and i > 0) else p.capitalize() for i, p in enumerate(palavras)
    )


# ----------------------------------------------------------------- extracao

def _pares_rotulo_valor(linhas: list[str]) -> list[tuple[str, str, str]]:
    """(chave, rotulo original, valor bruto) encontrados no texto.

    Reconhece tres layouts:

    - ``Rotulo: valor`` na mesma linha;
    - rotulo numa linha e valor na seguinte;
    - tabela: varios rotulos seguidos e, logo abaixo, a mesma quantidade de
      valores, pareados pela posicao (o cabecalho dos PDFs deste projeto).
    """
    pares: list[tuple[str, str, str]] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if ":" in linha:
            rotulo, _, valor = linha.partition(":")
            chave = _chave_do_rotulo(rotulo)
            if chave and valor.strip():
                pares.append((chave, rotulo.strip(), valor.strip()))
                i += 1
                continue

        # Junta os rotulos conhecidos consecutivos (1 = layout simples, 2+ = tabela).
        rotulos: list[tuple[str, str]] = []
        j = i
        while j < len(linhas) and _chave_do_rotulo(linhas[j]):
            rotulos.append((_chave_do_rotulo(linhas[j]), linhas[j].strip(" :")))
            j += 1
        if not rotulos:
            i += 1
            continue

        valores = linhas[j : j + len(rotulos)]
        if len(valores) == len(rotulos) and not any(_chave_do_rotulo(v) for v in valores):
            for (chave, rotulo), valor in zip(rotulos, valores):
                pares.append((chave, rotulo, valor))
            i = j + len(rotulos)
        else:
            i = j
    return pares


def _unicos(itens: list[Any]) -> list[Any]:
    vistos: list[Any] = []
    for item in itens:
        if item not in vistos:
            vistos.append(item)
    return vistos


def _encontrados(texto: str) -> dict[str, list[Any]]:
    """Valores com formato reconhecivel em qualquer parte do texto."""
    cnpjs = _unicos(_digitos(m) for m in _RE_CNPJ.findall(texto))
    # Um CNPJ sem pontuacao tambem casa com o padrao de CPF; por isso o CPF
    # so e aceito quando nao faz parte de um CNPJ ja encontrado.
    cpfs = _unicos(
        d for d in (_digitos(m) for m in _RE_CPF.findall(texto))
        if not any(d in c for c in cnpjs)
    )
    datas = _unicos(
        iso for iso in (
            normalizar_data(m.group(0))
            for m in (*_RE_DATA_BR.finditer(texto), *_RE_DATA_ISO.finditer(texto))
        ) if iso
    )
    valores = _unicos(
        v for v in (normalizar_dinheiro(m) for m in _RE_DINHEIRO.findall(texto)) if v is not None
    )
    return {
        "cpf": [{"valor": c, "formatado": formatar_cpf(c), "valido": cpf_valido(c)} for c in cpfs],
        "cnpj": [{"valor": c, "formatado": formatar_cnpj(c), "valido": cnpj_valido(c)} for c in cnpjs],
        "email": _unicos(m.lower() for m in _RE_EMAIL.findall(texto)),
        "telefone": _unicos(t for t in (formatar_telefone(m) for m in _RE_TELEFONE.findall(texto)) if t),
        "cep": _unicos(formatar_cep(m) for m in _RE_CEP.findall(texto)),
        "data": [{"valor": d, "formatado": formatar_data(d)} for d in datas],
        "dinheiro": [{"valor": v, "formatado": formatar_moeda(v)} for v in valores],
        "percentual": _unicos(" ".join(m.split()) for m in _RE_PERCENTUAL.findall(texto)),
    }


def _cliente(dados: dict[str, dict], encontrados: dict[str, list]) -> dict[str, Any]:
    """Dados do cliente nos nomes do contrato canonico (bloco ``cliente``)."""

    def valor(chave: str) -> Any:
        return dados[chave]["valor"] if chave in dados else None

    cpf = valor("cpf") or (encontrados["cpf"][0]["valor"] if encontrados["cpf"] else None)
    cnpj = valor("cnpj") or (encontrados["cnpj"][0]["valor"] if encontrados["cnpj"] else None)
    email = valor("email") or (encontrados["email"][0] if encontrados["email"] else None)
    telefone = valor("telefone") or (
        _digitos(encontrados["telefone"][0]) if encontrados["telefone"] else None
    )

    if cnpj and not cpf:
        cliente: dict[str, Any] = {
            "tipoPessoa": "PJ",
            "dadosPJ": {"razaoSocial": valor("razao_social") or valor("nome"), "cnpj": cnpj},
        }
    else:
        cliente = {
            "tipoPessoa": "PF" if cpf else None,
            "dadosPF": {
                "nomeCompleto": dados["nome"]["formatado"] if "nome" in dados else None,
                "cpf": cpf,
                "dataNascimento": valor("data_nascimento"),
            },
        }
    cliente["contato"] = {"email": email, "telefone": telefone}
    cliente["endereco"] = {"logradouro": valor("endereco"), "cep": valor("cep")}
    return _sem_vazios(cliente)


def _sem_vazios(dados: Any) -> Any:
    if isinstance(dados, dict):
        limpo = {k: _sem_vazios(v) for k, v in dados.items()}
        return {k: v for k, v in limpo.items() if v not in (None, "", {}, [])}
    return dados


def extrair_informacoes(texto: str) -> dict[str, Any]:
    """Organiza o texto de um PDF em campos normalizados e formatados."""
    linhas = [" ".join(linha.split()) for linha in texto.splitlines()]
    linhas = [linha for linha in linhas if linha]

    dados: dict[str, dict[str, Any]] = {}
    for chave, rotulo, bruto in _pares_rotulo_valor(linhas):
        if chave not in dados:  # vale a primeira ocorrencia valida
            campo = _normalizar_campo(chave, bruto)
            if campo is None:
                continue
            campo["rotulo"] = rotulo
            dados[chave] = campo

    encontrados = _encontrados(texto)
    return {
        "dados": dados,
        "encontrados": {k: v for k, v in encontrados.items() if v},
        "cliente": _cliente(dados, encontrados),
    }


def ler_e_formatar(caminho: str | Path, senha: str | None = None) -> dict[str, Any]:
    """Le o PDF e devolve arquivo, informacoes organizadas e o texto completo.

    Levanta ``leitor_pdf.ErroLeituraPdf`` quando o arquivo nao pode ser lido.
    """
    conteudo: ConteudoPdf = ler_pdf(caminho, senha=senha)
    return {
        "arquivo": {
            "numero_paginas": conteudo.numero_paginas,
            "metadados": conteudo.metadados,
            "hash_documento": conteudo.hash_documento,
        },
        "informacoes": extrair_informacoes(conteudo.texto),
        "texto": conteudo.paginas,
        "aviso_texto_vazio": (
            "Nenhum texto encontrado. O PDF provavelmente é escaneado (imagem) e "
            "precisaria de OCR."
            if not conteudo.texto.strip()
            else None
        ),
    }
