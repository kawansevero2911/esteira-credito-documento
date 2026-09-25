# Esteira de Crédito — Estruturação de Documentos

Repositório: https://github.com/kawansevero2911/esteira-credito-documento

## 1. Objetivo

Este projeto implementa o serviço responsável pela **estruturação e emissão de documentos da Esteira de Crédito**. O serviço recebe dados de uma operação em JSON, valida a estrutura recebida, mapeia os dados para um modelo documental, gera um PDF, registra os metadados do documento em armazenamento orientado a documentos e publica uma referência do documento gerado.

A solução é uma evolução do protótipo desenvolvido na primeira entrega da disciplina.

## 2. Escopo desta entrega

Nesta versão, o protótipo local foi organizado como uma API REST. O módulo possui uma interface para receber operações e consultar documentos gerados.

### Fluxo

```text
Cliente / outro módulo
        |
        v
POST /api/documentos
        |
        v
Validação do JSON Schema
        |
   +----+----+
   |         |
 inválido   válido
   |         |
   v         v
 erro      mapeamento
             |
             v
        geração do PDF
             |
             v
       armazenamento
             |
             v
      evento estruturado
             |
             v
          resposta
```

## 3. Endpoints

A documentação completa e interativa dos endpoints está no Swagger (`/docs`). Resumo:

| Método | Rota | Descrição | Respostas |
|---|---|---|---|
| GET | `/api/saude` | Verifica se a API está disponível | 200 |
| POST | `/api/documentos` | Valida a operação (JSON Schema) e executa o fluxo documental | 201, 400, 422 |
| GET | `/api/documentos/{documento_id}` | Consulta os metadados de um documento gerado | 200, 404 |

- **400 `DADOS_INVALIDOS`**: o JSON é um objeto, mas não atende ao contrato `OperacaoCredito`. Nenhum PDF é gerado.
- **422**: o corpo nem é um objeto JSON (erro de formato tratado pelo FastAPI).

## 4. Tecnologias## 4. Tecnologias

- Python 3.10+
- FastAPI
- Uvicorn
- JSON Schema / jsonschema
- ReportLab
- armazenamento local orientado a documentos para o protótipo

## 5. Execução

Crie um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Depois:

```bash
pip install -r requirements.txt
uvicorn src.api:app --reload
```

A API ficará disponível em:

```text
http://127.0.0.1:8000
```

Acessar `http://127.0.0.1:8000/` redireciona para a documentação.

## 5.1 Documentação Swagger / OpenAPI

| Endereço | Conteúdo |
|---|---|
| `http://127.0.0.1:8000/docs` | Swagger UI (interativo, com "Try it out") |
| `http://127.0.0.1:8000/redoc` | ReDoc (leitura) |
| `http://127.0.0.1:8000/openapi.json` | Especificação OpenAPI 3.1 em JSON |

O que está documentado no Swagger:

- descrição da API, do fluxo e um passo a passo de teste;
- endpoints agrupados por tag (**Infraestrutura** e **Documentos**), com resumo e descrição;
- corpo do `POST /api/documentos` usando o **próprio JSON Schema do contrato** (`schemas/operacao_credito.schema.json`), publicado como `OperacaoCredito`;
- exemplos prontos (`operacao_valida` e `operacao_invalida`) selecionáveis no "Try it out";
- modelos de resposta de sucesso e de erro (`DocumentoCriado`, `DocumentoMetadados`, `ErroDadosInvalidos`, `ErroNaoEncontrado`).

Para gerar o arquivo `docs/openapi.json` sem subir o servidor (útil para enviar aos outros grupos ou abrir no https://editor.swagger.io):

```bash
python -m scripts.exportar_openapi
```

Para rodar os testes (inclui testes da documentação Swagger):

```bash
pytest
```

## 6. Teste rápido

Com a API em execução, envie `examples/operacao_valida.json` para `POST /api/documentos`.

Exemplo com `curl`:

```bash
curl -X POST "http://127.0.0.1:8000/api/documentos" \
  -H "Content-Type: application/json" \
  --data-binary @examples/operacao_valida.json
```

Para testar a validação, envie `examples/operacao_invalida.json`.

## 7. Estrutura do projeto

```text
src/
  api.py                  # endpoints REST e configuração do Swagger/OpenAPI
  modelos.py              # modelos de resposta documentados no Swagger
  processo.py             # orquestração do processo documental
  validador.py            # validação JSON Schema
  mapeador.py             # mapeamento para o documento
  gerador_pdf.py          # geração do PDF
  repositorio.py          # armazenamento dos metadados
  publicador_evento.py    # publicação simulada do evento
schemas/
  operacao_credito.schema.json
examples/
  operacao_valida.json
  operacao_invalida.json
storage/
  pdfs/
  documentos/
  eventos/
scripts/
  exportar_openapi.py     # gera docs/openapi.json
docs/
  arquitetura.md
tests/
  test_api.py             # endpoints + documentação Swagger
mudancas.txt
requirements.txt
```

## 8. Integração com os demais grupos

A API foi estruturada para receber dados por contrato JSON. Os contratos definitivos dos módulos externos da Esteira — como Score, Decisão, Cálculo de Juros e Financiamento de Automóveis — ainda dependem do alinhamento entre os grupos e da disponibilização dos respectivos serviços.

Portanto, esta entrega não declara como implementada uma integração externa que ainda não foi disponibilizada. O projeto registra essa dependência e deixa a camada de entrada preparada para evolução do contrato.

## 9. Limitações conhecidas

- O armazenamento ainda é local, em arquivos JSON, funcionando como uma representação de repositório orientado a documentos.
- A publicação de evento ainda é simulada por um registro estruturado em arquivo JSON. Um barramento real poderá substituir essa implementação sem alterar o fluxo principal.
- O contrato da operação usado nesta entrega corresponde ao schema do protótipo e deverá ser versionado/evoluído conforme os contratos finais dos demais grupos.
- O template PDF é propositalmente simples nesta etapa.

## 10. Próximos passos

1. Refinar e versionar os contratos JSON com os demais grupos.
2. Substituir o armazenamento local por uma base orientada a documentos, se essa decisão for adotada pelo grupo.
3. Substituir a publicação simulada por um barramento compartilhado.
4. Evoluir os templates para diferentes produtos financeiros.
5. Manter a documentação Swagger atualizada a cada mudança de contrato.
6. Adicionar testes de integração com os serviços dos demais grupos quando os endpoints definitivos estiverem disponíveis.
