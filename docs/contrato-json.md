# Contrato JSON canônico da Esteira de Crédito

**Versão atual: 1.2.0**

Este documento descreve o contrato de entrada do Processo 6 — Estruturação de
Documentos Não Relacionais. Ele é também o **contrato canônico da Esteira**: a
mesma estrutura serve de meio de comunicação entre os 10 processos.

---

## 1. Princípio

Existe **um** contrato, dividido em **blocos**. Cada processo preenche apenas os
blocos pelos quais é responsável e ignora os demais. Nenhum processo é obrigado
a enviar campos que não lhe pertencem.

```json
{
  "schemaVersion": "1.2.0",
  "correlacao":         { },
  "documento":          { },
  "cliente":            { },
  "cadastro":           { },
  "promocao":           { },
  "credito":            { },
  "produtoFinanceiro":  { },
  "financiamento":      { },
  "score":              { },
  "juros":              { },
  "decisao":            { },
  "operacaoFinanceira": { },
  "metadados":          { }
}
```

Isso é o oposto de dez contratos isolados: uma operação de crédito PF, um
financiamento imobiliário e um financiamento automotivo usam a **mesma**
estrutura, mudando só quais blocos vêm preenchidos.

---

## 2. Responsabilidade de cada bloco

| Bloco | Processo responsável | Finalidade | Contrato |
|---|---|---|---|
| `correlacao` | comum a todos | identificadores de rastreio da operação | definido |
| `documento` | 6 — Estruturação de Documentos | qual documento emitir | definido |
| `cliente` | 3 — Crédito PF e PJ | identificação e dados cadastrais | definido para PF |
| `cadastro` | 3 — Crédito PF e PJ | perfil financeiro (entradas do Score) | definido |
| `promocao` | 1 — Promoções e Ações de Crédito | promoções aplicadas | **não definido** |
| `credito` | 3 — Crédito PF e PJ | solicitação de crédito PF/PJ | **não definido** |
| `produtoFinanceiro` | 7 — Produtos Financeiros | produto contratado | **não definido** |
| `financiamento` | 4 — Imóveis / 8 — Automotivo | dados do financiamento | imóveis definido; automotivo **não definido** |
| `score` | 10 — Score | resultado da avaliação de risco | definido |
| `juros` | 5 — Cálculo de Juros | resultado do cálculo financeiro | **não definido** |
| `decisao` | 9 — Decisão | resultado da análise | **parcial** |
| `operacaoFinanceira` | 2 — Controle Financeiro de Operações | operação contratada e cronograma | definido |
| `metadados` | comum a todos | rastreabilidade | definido |

> **Consolidação documentada.** O roteiro arquitetural previa os blocos
> `operacaoFinanceira` e `controleFinanceiro` separados. Os dois descreviam a
> mesma operação e o mesmo cronograma, produzidos pelo mesmo processo. Foram
> unificados em `operacaoFinanceira` para não duplicar informação.

---

## 3. O que é obrigatório

### Sempre

`schemaVersion`, `correlacao` (com `idOperacao`), `documento` (com
`tipoDocumento`) e `cliente` (com `tipoPessoa`).

### Por tipo de pessoa

| Condição | Exigência |
|---|---|
| `cliente.tipoPessoa = "PF"` | `cliente.dadosPF` com `nomeCompleto` e `cpf` |
| `cliente.tipoPessoa = "PJ"` | `cliente.dadosPJ` — **sem nenhum campo interno obrigatório** |

O bloco de PJ não exige nada por dentro porque o contrato de pessoa jurídica
ainda depende do grupo Crédito PF e PJ. Exigir campos ali seria inventar
requisito.

### Por produto

| Condição | Exigência |
|---|---|
| `financiamento.tipo = "IMOBILIARIO"` | `financiamento.imobiliario` (com `valorImovel`, `valorEntrada`, `prazoMeses`, `taxaJurosMensal`, `sistemaAmortizacao`), `cadastro.rendaMensal`, `cliente.endereco` (com `logradouro` e `cidade`) e, para PF, `cliente.dadosPF.dataNascimento` |
| `financiamento.tipo = "AUTOMOTIVO"` | `financiamento.automotivo` — **sem nenhum campo interno obrigatório** |

Uma operação automotiva **não** exige dados imobiliários, e vice-versa. As
regras estão no schema, em `allOf` / `if` / `then`, e portanto valem para
qualquer validador, em qualquer linguagem.

### Coerência entre blocos

| Condição | Exigência |
|---|---|
| `cliente.tipoPessoa = "PF"` **e** bloco `score` presente | `score.modelo.codigo = "SCORE_PF"` |
| `cliente.tipoPessoa = "PJ"` **e** bloco `score` presente | `score.modelo.codigo = "SCORE_PJ"` |

Nenhum campo novo é exigido aqui: os dois códigos de modelo e os dois tipos de
pessoa foram informados pelo grupo Score, e a correspondência entre eles é o
único pareamento possível entre os valores declarados. A verificação existe para
que um resultado calculado pelo modelo errado não entre no documento sem que
ninguém perceba.

---

## 4. Blocos estritos e blocos abertos

| Comportamento | Blocos | Motivo |
|---|---|---|
| `additionalProperties: false` (estrito) | raiz, `correlacao`, `documento`, `cliente`, `cadastro`, `score`, `financiamento`, `financiamento.imobiliario`, `operacaoFinanceira`, `metadados` | o contrato é conhecido; campo desconhecido é erro de integração e deve ser acusado |
| `additionalProperties: true` (aberto) | `promocao`, `credito`, `produtoFinanceiro`, `juros`, `decisao`, `financiamento.automotivo`, `cliente.dadosPJ` | o contrato **ainda não foi fornecido** pelo grupo responsável; o bloco aceita o que vier sem que nada seja inventado aqui |

Quando um grupo entregar seu contrato, o bloco correspondente passa a declarar
os campos e vira estrito — **sem reconstruir a estrutura**.

---

## 5. Regras de valor

| Regra | Onde vale | Origem |
|---|---|---|
| CPF: exatamente 11 dígitos, sem pontuação | `cliente.dadosPF.cpf` | grupo Financiamento de Imóveis |
| Datas: `YYYY-MM-DD` e existentes no calendário | `dataNascimento`, `vencimento`, `primeiroVencimento`, `dataAprovacao` | grupo Controle Financeiro |
| Timestamps: ISO-8601 **UTC** (`Z` ou `+00:00`) | `calculatedAt`, `criadoEm`, `atualizadoEm`, `decididoEm` | grupos Score e Controle Financeiro |
| Valores monetários: ≥ 0, no máximo **2 casas** | todos os campos de dinheiro | grupo Controle Financeiro |
| Taxa decimal: ≥ 0, no máximo **6 casas** | `operacaoFinanceira.taxaJuros`, `juros.taxaMensal` | grupo Controle Financeiro |
| Prazo: inteiro ≥ 1 | `prazoMeses`, `prazo` | grupo Financiamento de Imóveis |
| Score: inteiro de **0 a 1000** | `score.scoreFinal` | grupo Score |
| `numeroOperacao`: `OP-AAAA-NNNNNN` | `operacaoFinanceira.numeroOperacao` | grupo Controle Financeiro |

### Enums

| Campo | Valores |
|---|---|
| `cliente.tipoPessoa` | `PF`, `PJ` |
| `sistemaAmortizacao` | `SAC`, `PRICE` |
| `score.faixaRisco` | `EXCELENTE`, `BOM`, `REGULAR`, `CRITICO` |
| `score.modelo.codigo` | `SCORE_PF`, `SCORE_PJ` |
| `score.origem` | `CALCULO`, `BANCO` |
| `decisao.resultado` | `APROVADA`, `RECUSADA`, `ANALISE_MANUAL`, `APROVADO` |
| `financiamento.tipo` | `IMOBILIARIO`, `AUTOMOTIVO` |
| `documento.tipoDocumento` | `PROPOSTA_CREDITO` |
| `operacaoFinanceira.status` | `ATIVA` |
| `operacaoFinanceira.cronograma[].status` | `PENDENTE` |

`score.componentes` e `score.fatoresImpacto` **precisam existir**, mas podem ser
listas vazias — exigência explícita do grupo Score. `operacaoFinanceira.cronograma`
e `decisao.motivos` também aceitam lista vazia.

### Duas atenções sobre unidades

1. **Taxa de juros tem duas unidades diferentes na Esteira.**
   `financiamento.imobiliario.taxaJurosMensal` é **percentual** (`1.35` =
   1,35% a.m.), como declarou o grupo Financiamento de Imóveis.
   `operacaoFinanceira.taxaJuros` é **decimal** (`0.0199` = 1,99% a.m.), como
   declarou o grupo Controle Financeiro. As duas foram mantidas como os grupos
   informaram; unificá-las depende de alinhamento entre eles.

2. **Cidade aparece em dois lugares, com sentidos diferentes.**
   `cliente.endereco.cidade` é a cidade do cliente.
   `financiamento.imobiliario.cidade` é a cidade do imóvel.

---

## 6. A extensão `x-casasDecimais`

O limite de casas decimais **não** usa `multipleOf`. O motivo é concreto:
`multipleOf` opera em ponto flutuante e reprova valores válidos — `1234.56 /
0.01` resulta em `123455.99999999999`, e o valor seria recusado por engano.

Em vez disso, o contrato marca os campos com `x-casasDecimais`, e o validador
deste projeto compara casas decimais em `Decimal`, sem erro de arredondamento.

```json
"valorMonetario": { "type": "number", "minimum": 0, "x-casasDecimais": 2 }
```

**Consequência para quem integra em outra linguagem:** palavras-chave
desconhecidas são ignoradas pelo JSON Schema, então o seu validador vai aceitar
`400000.123`, mas **a nossa API vai recusar**. Arredonde no emissor.

---

## 7. Organização dos arquivos

```text
schemas/
├── operacao_credito.schema.json    ← contrato CONSOLIDADO (gerado; é o que se publica)
└── v1/                             ← FONTE: um arquivo por bloco
    ├── operacao_credito.schema.json    raiz, regras condicionais
    ├── comuns.schema.json              tipos reutilizados (CPF, data, moeda…)
    ├── correlacao.schema.json
    ├── documento.schema.json
    ├── cliente.schema.json
    ├── cadastro.schema.json
    ├── promocao.schema.json
    ├── credito.schema.json
    ├── produto_financeiro.schema.json
    ├── financiamento.schema.json
    ├── score.schema.json
    ├── juros.schema.json
    ├── decisao.schema.json
    ├── operacao_financeira.schema.json
    └── metadados.schema.json
```

**Edite sempre `schemas/v1/`.** Depois rode:

```bash
python -m scripts.gerar_bundle_schema
```

O arquivo consolidado fica versionado no repositório para que o caminho público
do contrato não mude e para que quem só quer o contrato não precise executar
nada. O teste `tests/test_contrato.py` falha se os dois ficarem fora de sincronia.

---

## 8. Versionamento

O formato é `MAIOR.MENOR.CORRECAO`, declarado em `schemaVersion` e validado
contra `^1\.[0-9]+\.[0-9]+$`.

| Tipo de mudança | Efeito na versão | Quebra quem já integra? |
|---|---|---|
| Campo opcional novo | MENOR (1.2.0 → 1.3.0) | não |
| Valor novo em um enum | MENOR | não |
| Bloco novo | MENOR | não |
| Campo opcional vira obrigatório | **MAIOR** | sim |
| Campo removido ou renomeado | **MAIOR** | sim |
| Valor removido de um enum | **MAIOR** | sim |
| Texto de descrição | CORREÇÃO | não |

**Toda a linha 1.x é compatível entre si.** Uma mudança incompatível cria
`schemas/v2/` ao lado de `schemas/v1/`, e as duas passam a conviver — nenhum
grupo é obrigado a migrar no mesmo dia.

### Histórico

| Versão | Mudança |
|---|---|
| 1.0.0 | contrato plano do protótipo: `id_operacao`, `tipo_produto`, `cliente`, `valor`, `prazo_meses`, `taxa_juros_mensal` |
| 1.1.0 | sem mudança de contrato; publicação do schema no Swagger |
| **1.2.0** | contrato canônico modular, em blocos por processo, com regras condicionais por produto e suporte a PF e PJ |

---

## 9. Compatibilidade com a versão 1.0.0

A API **continua aceitando** o formato plano antigo:

```json
{
  "id_operacao": "OP-2026-000999",
  "tipo_produto": "financiamento_automovel",
  "cliente": { "nome": "Cliente Exemplo", "documento": "000.000.000-00" },
  "valor": 45000.0,
  "prazo_meses": 48,
  "taxa_juros_mensal": 1.35
}
```

A detecção é segura: o contrato canônico usa camelCase e exige `schemaVersion`;
o formato antigo usa snake_case e tem `id_operacao` na raiz.

Mensagens antigas são **convertidas** para o contrato canônico e só então
validadas — existe um único contrato e um único ponto de validação. A resposta
informa o formato recebido em `formatoEntrada` (`canonico` ou `legado_v1`).

| Formato 1.0.0 | Contrato canônico |
|---|---|
| `id_operacao` | `correlacao.idOperacao` |
| `tipo_produto` | `produtoFinanceiro.categoria` (em MAIÚSCULAS) |
| `cliente.nome` | `cliente.dadosPF.nomeCompleto` (ou `dadosPJ.razaoSocial`) |
| `cliente.documento` | `cliente.dadosPF.cpf` (11 dígitos) ou `cliente.dadosPJ.cnpj` (14 dígitos) |
| `valor` | `credito.valorSolicitado` |
| `prazo_meses` | `credito.prazoMeses` |
| `taxa_juros_mensal` | `credito.taxaJurosMensalPercentual` |

A conversão remove a pontuação do documento e usa a quantidade de dígitos para
decidir PF ou PJ. **Não preenche campo ausente:** o que faltava continua
faltando, e a validação acusa normalmente.

Esta camada é um degrau de migração, não parte do contrato. Contratos novos
devem usar o formato canônico.

---

## 10. Pendências

O que **não** está definido e por isso não foi inventado:

| Pendência | Grupo responsável | Situação no contrato |
|---|---|---|
| Contrato de Promoções e Ações de Crédito | Processo 1 | bloco `promocao` existe e está aberto |
| Contrato de Crédito PF/PJ | Processo 3 | bloco `credito` aberto; `cliente.dadosPJ` sem campos obrigatórios |
| Contrato de Produtos Financeiros | Processo 7 | bloco `produtoFinanceiro` aberto |
| Contrato de Cálculo de Juros | Processo 5 | bloco `juros` aberto, com os 2 campos evidenciados |
| Contrato final de Decisão | Processo 9 | bloco `decisao` aberto, exige apenas `resultado` |
| Contrato de Financiamento Automotivo | Processo 8 | `financiamento.automotivo` aberto e sem campos |
| **Vocabulário da decisão** | Processo 9 | Financiamento de Imóveis usa `APROVADA`/`RECUSADA`/`ANALISE_MANUAL`; Controle Financeiro usa `APROVADO`. Os dois são aceitos até o alinhamento |
| **Unidade da taxa de juros** | Processos 4, 5 e 2 | percentual em um bloco, decimal em outro (ver seção 5) |
| Escala de `probabilidadeDefault` | Processo 10 | não se sabe se é 0–1 ou 0–100; só o piso 0 é validado |
| Escala de `comprometimentoRenda` | Processo 4 | mesma situação |
| Demais estados de `operacaoFinanceira.status` | Processo 2 | só `ATIVA` foi informado |
| Demais estados de `cronograma[].status` | Processo 2 | só `PENDENTE` foi informado |
| Estrutura de `score.fatoresImpacto[]` | Processo 10 | lista exigida, itens sem campos definidos |
| Matrícula do imóvel | Processo 4 | **não implementada pelo grupo**; não existe no contrato |
| Formato do `idOperacao` | todos | texto livre, sem padrão acordado |

Nenhuma dessas lacunas impede a integração: os blocos existem, aceitam o que os
grupos enviarem e serão fechados quando os contratos chegarem.
