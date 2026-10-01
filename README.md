# Esteira de Crédito — Estruturação de Documentos (Processo 6)

Repositório: https://github.com/kawansevero2911/esteira-credito-documento

**Contrato canônico: 1.2.0 · API: 1.2.0**

---

## 1. Objetivo

Este projeto implementa o **Processo 6 — Estruturação de Documentos Não
Relacionais (JSON, PDF)** da Esteira de Crédito. O serviço recebe uma operação
de crédito em JSON, valida contra o contrato, mapeia os dados para um modelo
documental, gera um PDF, armazena os metadados em um repositório orientado a
documentos e publica o evento `documento.gerado`.

O projeto é responsável por **estrutura, consistência e documentação do
contrato** — e não pela lógica de negócio dos outros processos. Score, juros,
decisão e risco são **recebidos** dos processos responsáveis e apresentados no
documento; nenhum deles é recalculado aqui.

## 2. O contrato canônico da Esteira

O grande ponto desta versão: o JSON deixou de ser específico deste serviço e
passou a ser o **contrato canônico da Esteira de Crédito** — um contrato único,
dividido em blocos, em que **cada processo preenche apenas o seu**.

```json
{
  "schemaVersion": "1.2.0",
  "correlacao": {}, "documento": {}, "cliente": {}, "cadastro": {},
  "promocao": {}, "credito": {}, "produtoFinanceiro": {}, "financiamento": {},
  "score": {}, "juros": {}, "decisao": {}, "operacaoFinanceira": {},
  "metadados": {}
}
```

| Bloco | Processo responsável |
|---|---|
| `correlacao`, `metadados` | comuns a todos |
| `documento` | 6 — Estruturação de Documentos |
| `cliente`, `cadastro`, `credito` | 3 — Crédito PF e PJ |
| `promocao` | 1 — Promoções e Ações de Crédito |
| `produtoFinanceiro` | 7 — Produtos Financeiros |
| `financiamento` | 4 — Imóveis / 8 — Automotivo |
| `score` | 10 — Score |
| `juros` | 5 — Cálculo de Juros |
| `decisao` | 9 — Decisão |
| `operacaoFinanceira` | 2 — Controle Financeiro de Operações |

Só `schemaVersion`, `correlacao`, `documento` e `cliente` são obrigatórios
sempre. O resto depende do produto, por regras condicionais dentro do próprio
schema — uma operação automotiva não exige dados imobiliários, e vice-versa. O
contrato suporta **PF e PJ**.

Blocos cujo contrato ainda não foi fornecido pelo grupo responsável existem,
aceitam o que vier e **não exigem nada** — em vez de ter campos inventados.

📄 **[docs/contrato-json.md](docs/contrato-json.md)** — contrato completo, regras,
versionamento e pendências.

## 3. Fluxo

```text
Outro processo da Esteira
        │
        ▼
POST /api/documentos
        │
        ▼
(formato v1.0.0? → converte para o contrato canônico)
        │
        ▼
validação JSON Schema
        │
   ┌────┴────┐
inválido   válido
   │         │
   ▼         ▼
HTTP 400   mapeamento → modelo documental
nenhum PDF        │
nenhum registro   ▼
nenhum evento   geração do PDF
                  │
                  ▼
            armazenamento dos metadados
                  │
                  ▼
          evento `documento.gerado`
                  │
                  ▼
              HTTP 201
```

A validação acontece **antes** do mapeamento e da geração do PDF. Entrada
inválida não deixa rastro nenhum — e há teste para isso.

📄 **[docs/fluxo-documental.md](docs/fluxo-documental.md)** — cada etapa em detalhe.

## 4. Endpoints

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| GET | `/api/saude` | Verifica se a API está disponível | 200 |
| POST | `/api/documentos` | Valida a operação e executa o fluxo documental | 201, 400, 422 |
| GET | `/api/documentos/{documento_id}` | Consulta os metadados de um documento gerado | 200, 404 |

- **400 `DADOS_INVALIDOS`** — o JSON é um objeto, mas não atende ao contrato.
  Todos os erros vêm de uma vez, em texto (`detalhes`) e estruturados (`erros`).
  Nenhum PDF é gerado.
- **422** — o corpo nem é um objeto JSON (tratado pelo FastAPI).

## 5. Execução

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api:app --reload
```

A API fica em `http://127.0.0.1:8000`; a raiz redireciona para a documentação.

| Endereço | Conteúdo |
|---|---|
| `/docs` | Swagger UI (interativo, com "Try it out") |
| `/redoc` | ReDoc (leitura) |
| `/openapi.json` | Especificação OpenAPI 3.1 |

### Teste rápido

```bash
curl -X POST "http://127.0.0.1:8000/api/documentos" \
  -H "Content-Type: application/json" \
  --data-binary @examples/operacao_completa.json
```

### Banco de provas (`web/index.html`)

Uma página para testar a API pelo navegador, sem Swagger e sem `curl`. Arquivo
único, sem build e sem dependências: os sete exemplos do repositório já vêm
embutidos.

```bash
uvicorn src.api:app --reload      # suba o backend
```

Depois abra `web/index.html` no navegador — ou, se estiver usando o servidor
de fumaça, acesse `http://127.0.0.1:8000/`, que já serve a página.

A tela escolhe um caso, deixa editar o JSON antes de enviar, e mostra o
veredito do contrato: o documento emitido (identificador, PDF, hash e evento)
ou a lista de campos recusados, cada um com o caminho, a regra violada e a
mensagem. Também consulta os metadados pelo `documento_id` e verifica
`GET /api/saude`.

Se alterar `examples/` ou `web/modelo.html`, regenere a página:

```bash
python -m scripts.gerar_frontend
```

O teste `tests/test_frontend.py` falha se a página gerada ficar diferente do
molde ou dos exemplos.

> **CORS.** Para a página funcionar aberta do disco, o serviço libera qualquer
> origem (`allow_origins=["*"]` em `src/api.py`). É adequado a um serviço de
> teste em `localhost`; antes de expor o serviço em rede, restrinja a lista.

### Sem conseguir instalar as dependências

Se a máquina não tiver acesso à rede para o `pip install`, há um servidor de
fumaça que sobe os mesmos três endpoints usando só a biblioteca padrão, e
serve o banco de provas na raiz:

```bash
python -m scripts.servidor_local   # abrir http://127.0.0.1:8000/
```

Ele serve para conferir o fluxo por HTTP (201, 400, 200, 404) e para
apresentar o projeto. **Não substitui o serviço oficial** e não tem Swagger
nem OpenAPI — as duas camadas chamam a mesma orquestração em `src/processo.py`,
então o corpo das respostas é o mesmo.

### Exemplos disponíveis

| Arquivo | Cenário |
|---|---|
| `examples/operacao_valida.json` | financiamento imobiliário PF |
| `examples/operacao_com_score.json` | com o bloco `score` |
| `examples/operacao_com_decisao.json` | com `juros` e `decisao` |
| `examples/operacao_completa.json` | a Esteira inteira, com cronograma de parcelas |
| `examples/operacao_credito_pj.json` | pessoa jurídica |
| `examples/legado_v1_plano.json` | formato plano da v1.0.0 (compatibilidade) |
| `examples/operacao_invalida.json` | erros variados → HTTP 400 |

Todos aparecem prontos no Swagger, em `POST /api/documentos` → **Try it out**.

## 6. Documentação Swagger / OpenAPI

O Swagger é gerado da própria API e publica **o mesmo contrato usado na
validação** — não existe um modelo escrito à parte que possa ficar diferente do
que a API realmente valida.

Cada bloco do contrato vira um componente com nome próprio (`Cliente`, `Score`,
`Decisao`, `OperacaoFinanceira`…), então quem integra abre bloco por bloco e vê
campos, tipos, enums, obrigatoriedade e descrições — inclusive as pendências.

Para gerar `docs/openapi.json` sem subir o servidor:

```bash
python -m scripts.exportar_openapi
```

## 7. Versionamento do contrato

O formato é `MAIOR.MENOR.CORRECAO`, declarado em `schemaVersion`.

- **Toda a linha 1.x é compatível entre si**: versões menores só acrescentam
  campos opcionais, valores de enum e blocos.
- Mudança incompatível cria `schemas/v2/` ao lado de `schemas/v1/`; as duas
  convivem e nenhum grupo é obrigado a migrar no mesmo dia.

| Versão | Mudança |
|---|---|
| 1.0.0 | contrato plano do protótipo |
| 1.1.0 | sem mudança de contrato; schema publicado no Swagger |
| **1.2.0** | contrato canônico modular, blocos por processo, regras por produto, PF e PJ |

### Como evoluir o contrato

1. Edite o bloco em `schemas/v1/<bloco>.schema.json` — **nunca** o arquivo
   consolidado.
2. Rode `python -m scripts.gerar_bundle_schema`.
3. Rode `pytest`. O teste de sincronia falha se você esquecer o passo 2.
4. Atualize a versão em `x-versaoContrato` e o histórico em
   `docs/contrato-json.md`.

### Compatibilidade com a v1.0.0

O formato plano antigo (`id_operacao`, `tipo_produto`, `valor`…) **continua
funcionando**: é convertido para o contrato canônico antes da validação. A
resposta informa o formato recebido em `formatoEntrada`. Tabela de conversão em
[docs/contrato-json.md](docs/contrato-json.md#9-compatibilidade-com-a-versão-100).

## 8. Testes

```bash
pytest
```

| Arquivo | Cobre |
|---|---|
| `tests/test_contrato.py` | módulos, consolidação, sincronia do arquivo publicado, componentes do OpenAPI |
| `tests/test_validacao.py` | CPF, datas, timestamps UTC, score 0–1000, enums, PF/PJ, SAC/PRICE, decisão, obrigatórios, arrays vazios, casas decimais |
| `tests/test_compatibilidade.py` | conversão do formato v1.0.0 |
| `tests/test_documento.py` | mapeamento, templates, PDF, paginação, repositório, evento, fluxo |
| `tests/test_api.py` | endpoints, respostas, Swagger e OpenAPI |
| `tests/test_frontend.py` | sincronia do banco de provas com `examples/` e o molde |

Garantias verificadas, entre outras: **JSON inválido não gera PDF**, nem
registro, nem evento; o contrato publicado no Swagger é idêntico ao usado na
validação; e o identificador da operação não vira caminho de arquivo.

## 9. Tecnologias

- Python 3.10+
- FastAPI · Uvicorn
- JSON Schema Draft 2020-12 (`jsonschema`)
- ReportLab (Platypus)
- Pydantic (apenas nas respostas)
- armazenamento local orientado a documentos

## 10. Estrutura do projeto

```text
src/
  api.py                  endpoints REST e Swagger/OpenAPI
  processo.py             orquestração do fluxo
  contrato.py             carga, consolidação e versionamento do schema
  compatibilidade.py      aceite do formato plano v1.0.0
  validador.py            validação JSON Schema + extensões
  mapeador.py             contrato → modelo documental
  modelo_documental.py    seções, campos e tabelas do documento
  gerador_pdf.py          emissão do PDF
  templates_pdf/          um arquivo por layout de produto
  repositorio.py          interface + armazenamento em arquivos JSON
  publicador_evento.py    interface + publicação em arquivo JSON
  modelos.py              modelos Pydantic das respostas
schemas/
  operacao_credito.schema.json   contrato consolidado (gerado)
  v1/                            fonte: um arquivo por bloco
examples/                        7 exemplos
web/
  modelo.html                    molde do banco de provas
  index.html                     banco de provas (gerado, com os exemplos)
scripts/
  gerar_bundle_schema.py         regera o contrato consolidado
  exportar_openapi.py            gera docs/openapi.json
  gerar_frontend.py              regera web/index.html
  servidor_local.py              servidor de fumaça, sem dependências
storage/                         pdfs/ documentos/ eventos/
tests/
docs/
  arquitetura.md  contrato-json.md  integracao.md  fluxo-documental.md
mudancas.txt
requirements.txt
```

## 11. Integração com os demais grupos

O Processo 6 se comunica por **HTTP + JSON + JSON Schema**. A linguagem de quem
integra não importa: Java, Go, Node.js, Python ou outra. Não há dependência de
framework, driver ou biblioteca compartilhada.

O serviço **não assume** que os outros estejam implementados: qualquer processo
pode chamar `POST /api/documentos` sozinho, preenchendo apenas os seus blocos. O
PDF registra no rodapé o que não foi recebido.

📄 **[docs/integracao.md](docs/integracao.md)** — o que cada processo envia, com
exemplos.

## 12. Limitações conhecidas

- O armazenamento é local, em arquivos JSON, funcionando como representação de
  um repositório orientado a documentos. A interface já existe para a troca.
- A publicação do evento é simulada em arquivo JSON. A interface já existe para
  a troca por um barramento real.
- Reemitir documento para a mesma operação **substitui o PDF anterior** (o nome
  vem do `idOperacao`). Cada emissão continua criando um registro de metadados
  próprio, com identificador e hash distintos.
- Só o documento `PROPOSTA_CREDITO` é emitido.
- Crédito PJ e financiamento automotivo usam o template genérico, porque seus
  dados ainda não foram definidos pelos grupos responsáveis.
- A extensão `x-casasDecimais` é ignorada por validadores de outras linguagens:
  o limite de casas decimais precisa ser respeitado pelo emissor.

## 13. Pendências que dependem de outros grupos

1. **Vocabulário da decisão** — Financiamento de Imóveis usa
   `APROVADA`/`RECUSADA`/`ANALISE_MANUAL`; Controle Financeiro usa `APROVADO`.
   Os dois são aceitos até o alinhamento com o grupo Decisão.
2. **Unidade da taxa de juros** — percentual no bloco `financiamento`, decimal
   em `operacaoFinanceira`, como cada grupo declarou.
3. **Contratos não fornecidos** — Processos 1, 5, 7, 8 e o contrato final do 9.
4. **Dados completos de PJ** — Processo 3.
5. **Demais estados** de `operacaoFinanceira.status` e `cronograma[].status`.
6. **Escalas** de `probabilidadeDefault` e `comprometimentoRenda` (0–1 ou 0–100).
7. **Matrícula do imóvel** — não implementada pelo grupo Financiamento de
   Imóveis; não existe no contrato.

Lista completa em
[docs/contrato-json.md](docs/contrato-json.md#10-pendências).

## 14. Próximos passos

1. Fechar os blocos abertos conforme os grupos entregarem seus contratos.
2. Alinhar o vocabulário da decisão e a unidade da taxa de juros.
3. Substituir o armazenamento local por uma base orientada a documentos.
4. Substituir a publicação simulada por um barramento real.
5. Criar templates próprios para crédito PJ e financiamento automotivo quando os
   dados existirem.
6. Adicionar testes de integração com os serviços dos demais grupos quando os
   endpoints definitivos estiverem disponíveis.
