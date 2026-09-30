# Arquitetura — Estruturação de Documentos (Processo 6)

## 1. Responsabilidade

O Processo 6 é responsável pela **estruturação e padronização documental** da
Esteira de Crédito: recebe dados de outros processos em JSON, valida contra o
contrato canônico, mapeia para um modelo documental, emite o PDF, armazena os
metadados e publica o evento `documento.gerado`.

**O que o Processo 6 faz:** garantir estrutura, consistência e documentação do
contrato.

**O que o Processo 6 não faz:** assumir a lógica de negócio dos outros
processos. Ele **não recalcula** score, juros, decisão, risco, parcelas nem
saldos — esses resultados são recebidos dos processos responsáveis e apenas
apresentados.

## 2. Camadas

```text
        HTTP
          │
          ▼
┌──────────────────────┐
│ API                  │  src/api.py
│                      │  endpoints, Swagger/OpenAPI. Sem regra de negócio.
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ ORQUESTRAÇÃO         │  src/processo.py
│                      │  a ORDEM do fluxo. Só chama as camadas abaixo.
└──────────┬───────────┘
           ├──────────────► src/compatibilidade.py   formato v1.0.0 → canônico
           ├──────────────► src/contrato.py          carrega/consolida o schema
           ▼
┌──────────────────────┐
│ VALIDAÇÃO            │  src/validador.py
│                      │  JSON Schema 2020-12 + format + x-casasDecimais
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ MAPEAMENTO           │  src/mapeador.py
│                      │  contrato → modelo documental. Formata; não calcula.
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ MODELO DOCUMENTAL    │  src/modelo_documental.py
│                      │  seções, campos, tabelas. Imutável.
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│ PDF                  │  src/gerador_pdf.py + src/templates_pdf/
│                      │  escolhe o template pela chave e pagina.
└──────────┬───────────┘
           ▼
┌──────────────────────┐   ┌──────────────────────┐
│ REPOSITÓRIO          │   │ EVENTO               │
│ src/repositorio.py   │   │ src/publicador_evento.py
│ interface + arquivos │   │ interface + arquivo  │
└──────────────────────┘   └──────────────────────┘
```

Cada camada conhece apenas a de baixo. O gerador de PDF não sabe o que é
`schemaVersion`; o validador não sabe o que é uma seção; o endpoint não sabe
como um PDF é montado.

O fluxo detalhado está em [fluxo-documental.md](fluxo-documental.md).

## 3. Decisões de arquitetura

### 3.1 Um contrato canônico, em blocos por processo

Em vez de dez contratos isolados, existe **um** contrato dividido em blocos, e
cada processo preenche apenas o seu. Uma operação de crédito PF, um
financiamento imobiliário e um financiamento automotivo usam a mesma estrutura.
Ver [contrato-json.md](contrato-json.md).

### 3.2 O schema é modular; o publicado é consolidado

A fonte da verdade são os arquivos de `schemas/v1/`, um por bloco: assim cada
grupo mexe no seu arquivo sem abrir um schema gigante. Para publicar, eles são
consolidados em um único arquivo autossuficiente
(`schemas/operacao_credito.schema.json`), que é o que outros grupos consomem e o
que o Swagger publica.

O arquivo consolidado fica **versionado no repositório** — quem só quer o
contrato não precisa executar nada — e um teste garante que ele nunca fique
diferente dos módulos.

### 3.3 A validação é do JSON Schema, não de código Python

A entrada é validada pelo próprio contrato, com a biblioteca `jsonschema`. Não
há regra de negócio reescrita em Python. Duas extensões foram necessárias
porque o JSON Schema padrão não resolve os casos:

- verificação de `format` (que por especificação é só anotação);
- `x-casasDecimais`, porque `multipleOf` erra em ponto flutuante.

Ambas estão documentadas em [contrato-json.md](contrato-json.md#6-a-extensão-x-casasdecimais).

### 3.4 Pydantic só nas respostas

Se a entrada fosse validada por modelo Pydantic, o FastAPI responderia **422**
em outro formato, e o erro `400 DADOS_INVALIDOS` combinado com os outros grupos
deixaria de existir. Por isso o Pydantic documenta e padroniza apenas as
**saídas**.

### 3.5 Blocos abertos para contratos que ainda não existem

Bloco cujo contrato o grupo responsável ainda não forneceu aceita propriedades
adicionais e não exige nada. É o oposto de inventar campos: a área arquitetural
existe, nada é exigido nem recusado, e a pendência fica registrada na descrição
do próprio schema.

### 3.6 Interfaces onde a evolução já está prevista

`RepositorioDocumentos` e `PublicadorEventos` são interfaces. A implementação
atual grava arquivos JSON locais. Trocar por MongoDB ou por um barramento real
é escrever uma classe nova — o fluxo não muda.

Nem MongoDB nem barramento real são exigidos nesta etapa.

### 3.7 Templates de PDF por produto, em registro

O template é escolhido por uma chave definida pelo mapeador, resolvida num
registro — não por `if` espalhado pelo gerador. Acrescentar um produto custa um
arquivo novo e duas linhas de registro. Produto sem template próprio cai no
genérico e continua gerando documento.

### 3.8 Compatibilidade com a versão 1.0.0

O formato plano antigo continua aceito: é **convertido** para o contrato
canônico e só então validado. Existe um único contrato e um único ponto de
validação; a camada de conversão é um degrau de migração, não parte do contrato.

## 4. Estrutura de pastas

```text
src/
  api.py                  endpoints REST, Swagger/OpenAPI
  processo.py             orquestração do fluxo
  contrato.py             carga, consolidação e versionamento do schema
  compatibilidade.py      aceite do formato plano v1.0.0
  validador.py            validação JSON Schema + extensões
  mapeador.py             contrato → modelo documental
  modelo_documental.py    seções, campos e tabelas do documento
  gerador_pdf.py          emissão do PDF (ReportLab/Platypus)
  templates_pdf/
    __init__.py           registro de templates
    base.py               blocos de montagem compartilhados
    proposta_credito.py   template genérico
    proposta_imobiliaria.py
  repositorio.py          interface + armazenamento em arquivos JSON
  publicador_evento.py    interface + publicação em arquivo JSON
  modelos.py              modelos Pydantic das respostas
schemas/
  operacao_credito.schema.json   contrato consolidado (gerado)
  v1/                            fonte: um arquivo por bloco
examples/                        7 exemplos, dos válidos ao inválido
scripts/
  gerar_bundle_schema.py         regera o contrato consolidado
  exportar_openapi.py            gera docs/openapi.json
storage/
  pdfs/  documentos/  eventos/
tests/
docs/
```

## 5. Princípio de evolução

As interfaces entre camadas são mantidas separadas para permitir:

- substituir o armazenamento local por uma base orientada a documentos;
- substituir a publicação local por um barramento compartilhado;
- acrescentar produtos financeiros e templates;
- fechar os blocos abertos quando os grupos entregarem seus contratos;
- criar `schemas/v2/` ao lado de `schemas/v1/` se houver mudança incompatível,
  sem obrigar todos os grupos a migrar no mesmo dia.

Nenhuma dessas evoluções exige reconstruir a estrutura.
