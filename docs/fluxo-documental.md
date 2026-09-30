# Fluxo documental — Processo 6

Como uma mensagem JSON vira um documento PDF com metadados armazenados e um
evento publicado.

---

## 1. O fluxo

```text
            OUTRO PROCESSO DA ESTEIRA
                      │
                      ▼
           POST /api/documentos
                      │
                      ▼
            recebimento do JSON
                      │
                      ▼
      formato plano da v1.0.0?  ──sim──►  conversão para o contrato canônico
                      │                                  │
                     não                                 │
                      └──────────────┬───────────────────┘
                                     ▼
                       validação (JSON Schema 2020-12)
                                     │
                          ┌──────────┴──────────┐
                          │   dados válidos?    │
                          └──────────┬──────────┘
                    NÃO ◄────────────┴────────────► SIM
                     │                               │
                     ▼                               ▼
         HTTP 400 DADOS_INVALIDOS            mapeamento para o
         + lista de erros                    modelo documental
         ───────────────────                          │
         nenhum PDF gerado                            ▼
         nenhum registro criado             escolha do template
         nenhum evento publicado                      │
                                                      ▼
                                              geração do PDF
                                                      │
                                                      ▼
                                          armazenamento dos metadados
                                                      │
                                                      ▼
                                        publicação de `documento.gerado`
                                                      │
                                                      ▼
                                              HTTP 201 + resposta
```

A ordem importa: **a validação acontece antes do mapeamento e da geração do
PDF**. Se ela falha, a função retorna na hora. É por isso que uma entrada
inválida não deixa rastro nenhum — e existe teste para isso
(`test_entrada_invalida_nao_gera_pdf_registro_nem_evento`).

---

## 2. Etapa por etapa

### 2.1 Recebimento — `src/api.py`

O endpoint recebe o corpo como JSON e **não** o valida com Pydantic. Se
validasse, o FastAPI responderia 422 em outro formato e o erro
`400 DADOS_INVALIDOS` combinado com os outros grupos deixaria de existir. O
Pydantic é usado apenas nas **respostas**, para documentá-las no Swagger.

O endpoint também não contém regra de negócio: chama `executar_processo`.

### 2.2 Compatibilidade — `src/compatibilidade.py`

Se a mensagem está no formato plano da v1.0.0, é convertida para o contrato
canônico. Detalhes em [contrato-json.md](contrato-json.md#9-compatibilidade-com-a-versão-100).

### 2.3 Validação — `src/validador.py`

Valida contra o contrato montado a partir de `schemas/v1/`. Duas extensões:

- **verificação de `format`**: por especificação, `format` é só uma anotação e
  a maioria dos validadores não a confere. Aqui `date`, `date-time`, `uuid` e
  `email` são verificados com a biblioteca padrão do Python, o que faz
  `2026-02-31` ser recusada como data inexistente, e não apenas conferida no
  formato pelo `pattern`;
- **`x-casasDecimais`**: limite de casas decimais em `Decimal`, porque
  `multipleOf` erra em ponto flutuante (ver
  [contrato-json.md](contrato-json.md#6-a-extensão-x-casasdecimais)).

Em caso de falha, devolve **todos** os problemas de uma vez, em duas formas:

```json
{
  "status": "erro",
  "codigo": "DADOS_INVALIDOS",
  "mensagem": "Os dados recebidos não atendem ao contrato JSON Schema.",
  "detalhes": ["cliente.dadosPF.cpf: '123.456.789-01' does not match '^[0-9]{11}$'"],
  "erros": [
    { "campo": "cliente.dadosPF.cpf", "mensagem": "…", "regra": "pattern" }
  ],
  "formatoEntrada": "canonico",
  "versaoContrato": "1.2.0"
}
```

`detalhes` mantém o formato de texto usado desde a v1.0.0; `erros` é a mesma
informação estruturada, mais simples de tratar em Java, Go ou JavaScript.

### 2.4 Mapeamento — `src/mapeador.py`

Transforma o contrato no **modelo documental**: seções, campos e tabelas já
formatados para leitura humana.

| Seção do documento | Bloco de origem |
|---|---|
| CLIENTE | `cliente` |
| PRODUTO | `produtoFinanceiro`, `financiamento.tipo`, `credito.finalidade` |
| IMÓVEL | `financiamento.imobiliario` (só quando `tipo = IMOBILIARIO`) |
| FINANCEIRO — PERFIL DO CLIENTE | `cadastro` |
| FINANCEIRO — CONDIÇÕES DA OPERAÇÃO | `credito`, `financiamento.imobiliario`, `juros` |
| ANÁLISE | `score` |
| DECISÃO | `decisao` |
| OPERAÇÃO | `operacaoFinanceira` |
| PARCELAS (tabela) | `operacaoFinanceira.cronograma` |
| METADADOS | `metadados`, `correlacao`, `schemaVersion` |

**Uma seção só aparece se o bloco correspondente veio.** O que faltou por
depender de outro processo é listado no rodapé do PDF, em "INFORMAÇÕES NÃO
RECEBIDAS" — em vez de sumir em silêncio, como se o dado não existisse.

O mapeador **formata**; não calcula. Ele não recalcula score, juros, decisão,
risco, parcelas nem saldos, e não preenche campo ausente com valor padrão. As
únicas transformações numéricas são de apresentação: `0.0199` vira
`1,99% ao mês` usando a equivalência que o próprio grupo Controle Financeiro
declarou.

### 2.5 Geração do PDF — `src/gerador_pdf.py` e `src/templates_pdf/`

O PDF é gerado **do modelo documental, nunca do JSON bruto**: o gerador não
conhece o contrato de entrada.

O template é escolhido por uma chave definida pelo mapeador:

| Chave | Quando | Arquivo |
|---|---|---|
| `proposta_imobiliaria` | `financiamento.tipo = IMOBILIARIO` ou `produtoFinanceiro.categoria = FINANCIAMENTO_IMOVEL` | `templates_pdf/proposta_imobiliaria.py` |
| `proposta_credito` | qualquer outro caso | `templates_pdf/proposta_credito.py` |

Produto sem template próprio cai no genérico e **continua gerando documento** —
crédito PJ e financiamento automotivo estão nessa situação, porque seus dados
ainda não foram definidos. Criar templates para eles agora seria inventar layout
para dado que não chegou.

**Para acrescentar um produto:**

1. crie `src/templates_pdf/<produto>.py` com `CHAVE`, `DESCRICAO` e `montar`;
2. registre em `TEMPLATES`, em `templates_pdf/__init__.py`;
3. ligue o produto à chave em `mapeador.TEMPLATES_POR_PRODUTO`.

Nenhum outro arquivo muda.

A montagem usa o **Platypus** do ReportLab (e não desenho direto no canvas)
porque o cronograma pode passar de 300 parcelas: o Platypus quebra a tabela
entre páginas e repete o cabeçalho sozinho.

### 2.6 Armazenamento — `src/repositorio.py`

O registro é gravado como **documento**, não como linha de tabela:

```json
{
  "_id": "3f1c2a9e-…",
  "documento_id": "3f1c2a9e-…",
  "id_operacao": "OP-2026-000123",
  "criado_em": "2026-09-25T23:10:00+00:00",
  "tipo_documento": "PROPOSTA_CREDITO",
  "tipo_produto": "FINANCIAMENTO_IMOVEL",
  "versao_schema": "1.2.0",
  "caminho_pdf": "storage/pdfs/OP-2026-000123.pdf",
  "status": "GERADO",
  "hash_documento": "sha256:…",
  "template": "proposta_imobiliaria",
  "correlacao": { "idOperacao": "OP-2026-000123", "idCliente": "CLI-…" }
}
```

`_id` repete `documento_id` porque era a chave da v1.0.0 e há consumidores que
a leem.

`RepositorioDocumentos` é uma **interface**; `RepositorioArquivosJson` é a
implementação atual. Trocar por MongoDB é escrever uma classe nova — o fluxo não
muda. **MongoDB não é exigido nesta etapa.**

### 2.7 Evento — `src/publicador_evento.py`

```json
{
  "eventType": "documento.gerado",
  "eventVersion": "1.0",
  "eventId": "…",
  "occurredAt": "2026-09-25T23:10:00+00:00",
  "idOperacao": "OP-2026-000123",
  "documentoId": "3f1c2a9e-…",
  "tipoDocumento": "PROPOSTA_CREDITO",
  "schemaVersion": "1.2.0",
  "referencia": {
    "caminhoPdf": "storage/pdfs/OP-2026-000123.pdf",
    "hashDocumento": "sha256:…",
    "correlacao": { "idOperacao": "OP-2026-000123" }
  },

  "evento": "documento.gerado",
  "documento_id": "3f1c2a9e-…",
  "id_operacao": "OP-2026-000123",
  "caminho_pdf": "storage/pdfs/OP-2026-000123.pdf",
  "publicado_em": "2026-09-25T23:10:00+00:00"
}
```

Os campos em snake_case no final repetem informação já presente acima e existem
só por compatibilidade com os consumidores da v1.0.0.

A publicação continua **simulada**, em arquivo JSON. `PublicadorEventos` é uma
interface: um barramento real (Kafka, RabbitMQ) entra como outra implementação.
**Nenhum barramento real é exigido nesta etapa.**

---

## 3. Separação de responsabilidades

```text
API            src/api.py                 HTTP, Swagger. Sem regra de negócio.
ORQUESTRAÇÃO   src/processo.py            a ORDEM do fluxo. Só chama os outros.
COMPATIBILIDADE src/compatibilidade.py    formato v1.0.0 → contrato canônico
CONTRATO       src/contrato.py            carrega, consolida e versiona o schema
VALIDAÇÃO      src/validador.py           JSON Schema + format + x-casasDecimais
MAPEAMENTO     src/mapeador.py            contrato → modelo documental
DOCUMENTO      src/modelo_documental.py   seções, campos, tabelas (imutável)
PDF            src/gerador_pdf.py         escolhe o template e pagina
               src/templates_pdf/         um arquivo por layout
REPOSITÓRIO    src/repositorio.py         interface + arquivos JSON
EVENTO         src/publicador_evento.py   interface + arquivo JSON
RESPOSTAS      src/modelos.py             modelos Pydantic (só saída)
```

Cada camada conhece apenas a de baixo. O gerador de PDF não sabe o que é
`schemaVersion`; o validador não sabe o que é uma seção; o endpoint não sabe
como um PDF é montado.

---

## 4. Limites conhecidos

- **Reemitir para a mesma operação substitui o PDF.** O nome do arquivo vem do
  `idOperacao`, então a segunda emissão sobrescreve a primeira. Cada emissão
  continua criando um registro de metadados próprio, com identificador e hash
  distintos, então o histórico não se perde — mas o arquivo anterior sim.
- **O identificador da operação é higienizado** antes de virar nome de arquivo:
  ele vem de outro processo e não tem formato padronizado. Sem isso, um
  `idOperacao` como `../../x` escreveria fora da pasta de armazenamento.
- O armazenamento e a publicação de eventos são locais.
- Só o documento `PROPOSTA_CREDITO` é emitido.
