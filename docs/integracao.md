# Integração com os demais processos da Esteira

Guia para quem vai enviar dados ao Processo 6 — Estruturação de Documentos.

---

## 1. Como integrar, independentemente da linguagem

A comunicação é **HTTP + JSON + JSON Schema**. O Processo 6 não sabe — nem
precisa saber — se do outro lado há Java, Go, Node.js ou Python. Não há
dependência de framework, driver ou biblioteca compartilhada.

```text
    Java          Node.js          Go           Python
      │              │              │              │
      └──────────────┴──────┬───────┴──────────────┘
                            │  HTTP POST, corpo JSON
                            ▼
                   POST /api/documentos
                            │
                            ▼
              contrato canônico (JSON Schema 2020-12)
```

Para validar o contrato do seu lado **antes** de enviar, use
`schemas/operacao_credito.schema.json` — é um JSON Schema Draft 2020-12
autossuficiente, sem referências externas. Bibliotecas comuns:

| Linguagem | Biblioteca |
|---|---|
| Java | `networknt/json-schema-validator`, `everit-org/json-schema` |
| JavaScript / TypeScript | `ajv` (com `ajv-formats`) |
| Go | `santhosh-tekuri/jsonschema` |
| Python | `jsonschema` |
| .NET | `Newtonsoft.Json.Schema` |

> Lembre-se de `x-casasDecimais`: validadores padrão ignoram essa extensão e
> aceitarão `400000.123`, mas a nossa API recusa. Arredonde no emissor.
> Ver [contrato-json.md](contrato-json.md#6-a-extensão-x-casasdecimais).

---

## 2. Onde o Processo 6 fica no fluxo da Esteira

```text
                    CLIENTE
                       │
                       ▼
              CADASTRO (Processo 3)
                       │
                       ▼
         PRODUTO FINANCEIRO (Processo 7)
                       │
                       ▼
          SOLICITAÇÃO DE CRÉDITO / FINANCIAMENTO
              (Processos 3, 4 e 8)
                       │
                       ▼
                 SCORE (Processo 10)
                       │
                       ▼
                DECISÃO (Processo 9)
                       │
                       ▼
            CÁLCULO DE JUROS (Processo 5)
                       │
                       ▼
     CONTROLE FINANCEIRO DE OPERAÇÕES (Processo 2)
                       │
                       ▼
      ESTRUTURAÇÃO DE DOCUMENTOS (Processo 6)  ◄── aqui
```

E a cadeia que os grupos já confirmaram:

```text
SCORE  ──►  DECISÃO  ──►  JUROS  ──►  CONTROLE FINANCEIRO
```

> O grupo Controle Financeiro recebe hoje os dados **direto da Decisão**. A
> etapa de Juros entre as duas é a evolução prevista, ainda não implementada.

**O Processo 6 não assume que os demais serviços existam.** Qualquer processo
pode chamar `POST /api/documentos` sozinho, preenchendo apenas os seus blocos.
Uma operação só com `cliente` e `financiamento` gera documento normalmente — o
PDF apenas registra, no rodapé, o que não foi recebido.

---

## 3. O que cada processo envia

### Processo 1 — Promoções e Ações de Crédito

Bloco `promocao`. **Contrato ainda não fornecido**: o bloco aceita qualquer
conteúdo e não exige nada. Envie o que tiver; quando o contrato existir, ele
será declarado sem mudar a estrutura.

### Processo 2 — Controle Financeiro de Operações

Bloco `operacaoFinanceira`.

```json
{
  "operacaoFinanceira": {
    "id": "3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42",
    "numeroOperacao": "OP-2026-000400",
    "status": "ATIVA",
    "valorAprovado": 320000.00,
    "saldoDevedor": 320000.00,
    "prazo": 240,
    "quantidadeParcelas": 240,
    "taxaJuros": 0.0199,
    "sistemaAmortizacao": "PRICE",
    "primeiroVencimento": "2026-11-05",
    "dataAprovacao": "2026-09-25",
    "criadoEm": "2026-09-25T18:35:00Z",
    "cronograma": [
      {
        "numero": 1,
        "vencimento": "2026-11-05",
        "valorParcela": 2800.00,
        "valorAmortizacao": 1500.00,
        "juros": 1300.00,
        "saldoDevedorAposParcela": 318500.00,
        "status": "PENDENTE"
      }
    ]
  }
}
```

Obrigatórios: `numeroOperacao` e `status`. O `cronograma` pode vir vazio. Cada
parcela, porém, precisa vir **completa** — uma parcela pela metade não descreve
nada.

`taxaJuros` é **decimal** (`0.0199` = 1,99% a.m.), como o grupo informou.

O serviço do grupo usa Go, Gin e PostgreSQL. Nada disso é dependência daqui.

### Processo 3 — Crédito PF e PJ

Blocos `cliente`, `cadastro` e `credito`.

```json
{
  "cliente": {
    "tipoPessoa": "PF",
    "dadosPF": {
      "nomeCompleto": "Cliente Exemplo",
      "cpf": "12345678901",
      "dataNascimento": "1990-05-12",
      "idade": 36,
      "estadoCivil": "CASADO",
      "numeroDependentes": 2
    },
    "contato": { "telefone": "(81) 90000-0000", "email": "cliente@example.com" },
    "endereco": { "logradouro": "Rua Exemplo", "numero": "100",
                  "cidade": "Recife", "estado": "PE", "cep": "50000000" }
  },
  "cadastro": {
    "rendaMensal": 8500.00,
    "dividaTotal": 12000.00,
    "diasAtrasoUltimos12Meses": 0,
    "limiteRotativoUtilizado": 800.00,
    "limiteRotativoTotal": 9000.00,
    "mesesNoEmpregoAtual": 48,
    "mesesRelacionamentoBanco": 72
  }
}
```

Para PJ, use `dadosPJ` — que **não exige nenhum campo**, porque o contrato de
pessoa jurídica ainda depende deste grupo. O bloco `credito` também está aberto.

### Processo 4 — Financiamento de Imóveis

Bloco `financiamento`, com `tipo: "IMOBILIARIO"`.

```json
{
  "financiamento": {
    "tipo": "IMOBILIARIO",
    "imobiliario": {
      "tipoImovel": "APARTAMENTO",
      "cidade": "Recife",
      "estado": "PE",
      "valorImovel": 400000.00,
      "valorEntrada": 80000.00,
      "valorFinanciado": 320000.00,
      "prazoMeses": 360,
      "taxaJurosMensal": 0.95,
      "sistemaAmortizacao": "SAC",
      "valorPrimeiraParcela": 3450.00,
      "valorUltimaParcela": 895.00,
      "totalJurosEstimado": 462000.00,
      "totalPagoEstimado": 782000.00,
      "comprometimentoRenda": 28.5
    }
  }
}
```

Obrigatórios dentro de `imobiliario`: `valorImovel`, `valorEntrada`,
`prazoMeses`, `taxaJurosMensal` e `sistemaAmortizacao`. Enviar
`financiamento.tipo = "IMOBILIARIO"` também torna obrigatórios
`cadastro.rendaMensal`, `cliente.endereco` (com `logradouro` e `cidade`) e, para
PF, `cliente.dadosPF.dataNascimento` — exatamente os campos que o grupo declarou
como obrigatórios.

Os campos calculados pelo grupo (valor financiado, parcelas, totais,
comprometimento) são **opcionais**: o Processo 6 apenas apresenta o que recebe e
não recalcula nenhum deles.

`taxaJurosMensal` é **percentual** (`0.95` = 0,95% a.m.), como o grupo informou.

`cidade` e `estado` aqui são do **imóvel**; os do cliente ficam em
`cliente.endereco`.

> A **matrícula do imóvel** não foi implementada pelo grupo e portanto não
> existe no contrato.

### Processo 5 — Cálculo de Juros

Bloco `juros`. **Contrato ainda não fornecido.** O bloco existe e está aberto.
Os dois únicos campos declarados são os que têm evidência nos requisitos, por
aparecerem na entrada do Controle Financeiro:

```json
{ "juros": { "taxaMensal": 0.0199, "sistemaAmortizacao": "PRICE",
             "calculadoEm": "2026-09-25T18:31:00Z" } }
```

### Processo 7 — Produtos Financeiros

Bloco `produtoFinanceiro`. **Contrato ainda não fornecido**; o bloco está
aberto. O campo `categoria` existe porque seus valores vêm do `tipo_produto` do
contrato v1.0.0 deste projeto — não foram inventados — e é o que permite ao
Processo 6 escolher o template quando não há bloco `financiamento`.

```json
{ "produtoFinanceiro": { "categoria": "FINANCIAMENTO_IMOVEL",
                         "codigo": "PROD-IMOB-001", "nome": "Financiamento Exemplo" } }
```

### Processo 8 — Financiamento Automotivo

Bloco `financiamento`, com `tipo: "AUTOMOTIVO"` e o sub-bloco `automotivo`.
**Contrato ainda não fornecido**: `automotivo` não declara campo nenhum e aceita
o que vier. Dados imobiliários **não** são exigidos.

```json
{ "financiamento": { "tipo": "AUTOMOTIVO", "automotivo": { } } }
```

### Processo 9 — Decisão

Bloco `decisao`. **Contrato final ainda não fornecido**; o bloco está aberto e
exige apenas `resultado`.

```json
{
  "decisao": {
    "resultado": "APROVADA",
    "motivos": ["Score dentro da faixa EXCELENTE"],
    "versaoPolitica": "POL-2026.09",
    "dataAprovacao": "2026-09-25",
    "valorAprovado": 500000.00,
    "decididoEm": "2026-09-25T18:25:00Z"
  }
}
```

> **Divergência de vocabulário, ainda não resolvida.** O grupo Financiamento de
> Imóveis informou `APROVADA`, `RECUSADA` e `ANALISE_MANUAL`; o grupo Controle
> Financeiro informou `APROVADO`. Os quatro valores são aceitos para não
> bloquear nenhum dos grupos. Precisa de alinhamento com o grupo Decisão.

### Processo 10 — Score

Bloco `score`.

```json
{
  "score": {
    "scoreFinal": 742,
    "faixaRisco": "BOM",
    "probabilidadeDefault": 0.087,
    "modelo": { "codigo": "SCORE_PF", "versao": "v1.1.0" },
    "calculatedAt": "2026-09-25T18:30:00Z",
    "origem": "CALCULO",
    "componentes": [
      { "nome": "Renda comprometida", "pontuacao": 180,
        "pontuacaoMaxima": 250, "pesoPonderado": 0.30, "motivo": "…" }
    ],
    "fatoresImpacto": []
  }
}
```

Todos os campos acima são obrigatórios quando o bloco é enviado — foram todos
declarados pelo grupo. `componentes` e `fatoresImpacto` **precisam existir**,
mas podem ser listas vazias.

Dois campos da saída original **não** se repetem aqui: `clienteId` e
`tipoPessoa`. Eles são lidos de `correlacao.idCliente` e `cliente.tipoPessoa`,
para a mesma informação não existir em dois blocos. As **entradas** do cálculo
(renda, dívida, atrasos, tempo de emprego) ficam em `cadastro`, e idade, estado
civil e dependentes em `cliente.dadosPF`.

O código do modelo precisa combinar com o tipo de pessoa: `SCORE_PF` para PF.

---

## 4. Rastreabilidade entre processos

```json
{
  "correlacao": {
    "idOperacao": "OP-2026-000400",
    "idCliente": "CLI-EXEMPLO-0004",
    "idProposta": "PROP-EXEMPLO-0004",
    "idDocumento": "3f1c2a9e-…"
  },
  "metadados": {
    "origem": "CONTROLE_FINANCEIRO_OPERACOES",
    "criadoEm": "2026-09-25T18:28:00Z",
    "atualizadoEm": "2026-09-25T18:35:00Z",
    "processosParticipantes": ["SCORE", "DECISAO", "CONTROLE_FINANCEIRO_OPERACOES"]
  }
}
```

`idOperacao` é o **único identificador obrigatório** e é o que amarra a operação
de ponta a ponta. Identificadores próprios de cada processo continuam existindo
nos seus blocos — `operacaoFinanceira.id`, `operacaoFinanceira.numeroOperacao`,
`score.modelo.versao` — sem que o identificador de correlação se perca.

`processosParticipantes` aceita: `PROMOCOES_ACOES_CREDITO`,
`CONTROLE_FINANCEIRO_OPERACOES`, `CREDITO_PF_PJ`, `FINANCIAMENTO_IMOVEIS`,
`CALCULO_JUROS`, `ESTRUTURACAO_DOCUMENTOS`, `PRODUTOS_FINANCEIROS`,
`FINANCIAMENTO_AUTOMOTIVO`, `DECISAO`, `SCORE`.

---

## 5. O que o Processo 6 devolve

### Sucesso — HTTP 201

```json
{
  "status": "sucesso",
  "documento_id": "3f1c2a9e-8d4b-4c1e-9a55-2b7f0c6d1e42",
  "formatoEntrada": "canonico",
  "documento": {
    "documento_id": "3f1c2a9e-…",
    "id_operacao": "OP-2026-000400",
    "tipo_documento": "PROPOSTA_CREDITO",
    "tipo_produto": "FINANCIAMENTO_IMOVEL",
    "versao_schema": "1.2.0",
    "caminho_pdf": "storage/pdfs/OP-2026-000400.pdf",
    "status": "GERADO",
    "hash_documento": "sha256:…",
    "template": "proposta_imobiliaria"
  },
  "evento": { "eventType": "documento.gerado", "…": "…" }
}
```

### Erro de contrato — HTTP 400

```json
{
  "status": "erro",
  "codigo": "DADOS_INVALIDOS",
  "mensagem": "Os dados recebidos não atendem ao contrato JSON Schema.",
  "detalhes": ["score.scoreFinal: 1500 is greater than the maximum of 1000"],
  "erros": [{ "campo": "score.scoreFinal", "mensagem": "…", "regra": "maximum" }],
  "formatoEntrada": "canonico",
  "versaoContrato": "1.2.0"
}
```

Todos os problemas vêm de uma vez — não é preciso reenviar para descobrir o
próximo. **Nenhum PDF é gerado e nenhum registro é criado.**

### Corpo que nem é objeto JSON — HTTP 422

Tratado pelo FastAPI, antes do contrato.

---

## 6. Consumindo o evento `documento.gerado`

Publicado a cada documento emitido, hoje em arquivo JSON em `storage/eventos/`.
Formato completo em [fluxo-documental.md](fluxo-documental.md#27-evento---srcpublicador_eventopy).

Ao consumir, use os campos **novos** (`eventType`, `documentoId`, `idOperacao`,
`referencia`). Os campos em snake_case existem só por compatibilidade com a
v1.0.0 e não devem ser usados em integrações novas.

Um barramento real (Kafka, RabbitMQ) entra como outra implementação de
`PublicadorEventos`, sem alterar o fluxo nem o formato da mensagem.

---

## 7. Como testar a integração

1. Suba a API: `uvicorn src.api:app --reload`
2. Abra `http://127.0.0.1:8000/docs`
3. Em `POST /api/documentos` → **Try it out**, escolha um dos exemplos prontos
4. **Execute**, copie o `documento_id` e consulte em `GET /api/documentos/{documento_id}`

Ou por `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/documentos" \
  -H "Content-Type: application/json" \
  --data-binary @examples/operacao_completa.json
```

Exemplos disponíveis, todos em `examples/`:

| Arquivo | Cenário |
|---|---|
| `operacao_valida.json` | financiamento imobiliário PF |
| `operacao_com_score.json` | com o bloco `score` |
| `operacao_com_decisao.json` | com `juros` e `decisao` |
| `operacao_completa.json` | a Esteira inteira, com cronograma |
| `operacao_credito_pj.json` | pessoa jurídica |
| `legado_v1_plano.json` | formato plano da v1.0.0 |
| `operacao_invalida.json` | erros variados → HTTP 400 |

---

## 8. Pendências que dependem dos outros grupos

A lista completa está em
[contrato-json.md](contrato-json.md#10-pendências). As que mais afetam a
integração:

1. **Vocabulário da decisão** — `APROVADA` vs `APROVADO` (Processo 9).
2. **Unidade da taxa de juros** — percentual (Processo 4) vs decimal (Processo 2).
3. **Contratos não fornecidos** — Processos 1, 5, 7, 8 e o contrato final do 9.
4. **Dados completos de PJ** — Processo 3.
5. **Estados de `status`** — só `ATIVA` e `PENDENTE` foram informados (Processo 2).
6. **Escalas de `probabilidadeDefault` e `comprometimentoRenda`** — 0–1 ou 0–100?

Nenhuma dessas lacunas impede integrar agora: os blocos existem e aceitam o que
os grupos enviarem.
