# Esteira de Crédito — Grupo 6: Estruturação de Documentos (v1.4.0)

**Entrega acadêmica demonstrável.** Serviço independente em Python/FastAPI que valida JSON, gera PDFs, persiste metadados em JSON ou MongoDB e registra eventos `documento.gerado` localmente. Inclui integração somente leitura com **FinOps** e **CredCasa** e importação offline do JSON do grupo **Juros**. Não altera código nem registros de outros grupos.

## Início rápido — Windows (sem Docker)

1. Clone o repositório (`git clone https://github.com/kawansevero2911/esteira-credito-documento`) e abra a pasta no VS Code.
2. No terminal PowerShell, execute:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn src.app:app --reload
```

3. Acesse **http://127.0.0.1:8000/docs**. Para testar **sem outras APIs**, use `POST /api/documentos/finops` com `exemplos/finops_consulta_exemplo.json` ou `POST /api/documentos/credcasa` com `exemplos/credcasa_proposta_exemplo.json`.
4. Copie `documento_id` da resposta e abra `GET /api/documentos/{documento_id}/pdf` no Swagger para baixar o PDF.
5. Testes: `.\.venv\Scripts\python.exe -m pytest -q`.

## Endpoints

| Método | Caminho | Função |
|---|---|---|
| GET | `/api/saude` | Estado do serviço |
| GET | `/docs` | Swagger |
| POST | `/api/documentos` | Operação do contrato original v1 |
| POST | `/api/documentos/finops` | JSON FinOps local/offline |
| POST | `/api/documentos/finops/{identificador}/consultar` | Consulta FinOps via GET e emite PDF |
| POST | `/api/documentos/credcasa` | JSON CredCasa local/offline |
| POST | `/api/documentos/credcasa/{identificador}/consultar` | Consulta CredCasa via GET e emite PDF |
| GET | `/api/documentos/{documento_id}` | Metadados |
| GET | `/api/documentos/{documento_id}/pdf` | PDF |
| GET | `/api/schemas/operacao-credito` | JSON Schema do contrato original |
| GET | `/api/schemas/credcasa` | Contrato mínimo CredCasa |
| GET | `/api/schemas/juros` | Contrato JSON do grupo Juros |
| POST | `/api/documentos/juros` | JSON Juros local/offline (PDF SAC/PRICE) |

**ATENÇÃO:** endpoints `POST .../consultar` apenas fazem **GET nos sistemas externos** e criam o PDF localmente. Nenhuma operação financeira é criada/alterada nos sistemas de origem.

## Integração com FinOps

- URL padrão: `http://localhost:8083` (configurável com `FINOPS_URL`).
- O serviço lê `GET /operacoes/{identificador}` e `GET /operacoes/{identificador}/parcelas`.
- Exemplo: `POST /api/documentos/finops/OP-2026-0001/consultar`.
- É necessário que o FinOps esteja rodando e que a operação exista; **o ZIP não inclui o servidor FinOps nem seus dados**.

## Integração com CredCasa

- URL padrão: `https://credcasa-esteira-credito.onrender.com` (configurável com `CREDCASA_URL`).
- O serviço lê `GET /api/esteira/{id}`.
- Exemplo: `POST /api/documentos/credcasa/FIN-ID-REAL/consultar`.
- Necessário um ID real. O **formato completo do JSON ao vivo ainda não foi validado**: o contrato mínimo e o PDF foram baseados no exemplo fornecido pelo grupo de Imóveis. Caso o endpoint retorne um envelope JSON diferente, o adaptador precisará ser ajustado, sem alterar o CredCasa.

## MongoDB opcional com Docker

O sistema **funciona sem Docker**, armazenando metadados como JSON em `storage/documentos/` e PDFs em `storage/pdfs/`.

Para usar MongoDB:

```powershell
docker compose up -d
$env:MONGODB_URI="mongodb://localhost:27017"
.\.venv\Scripts\python.exe -m uvicorn src.app:app --reload
```

A coleção `esteira_credito.documentos` armazena os metadados, e os PDFs continuam no disco. Para voltar ao modo sem MongoDB, abra um novo terminal sem `MONGODB_URI`.

## Arquitetura e limitações honestas

- `src/app.py`: API/Swagger.
- `src/processo.py`: orquestração do contrato original.
- `src/integracao_finops.py`: consulta, validação e PDF do FinOps.
- `src/integracao_credcasa.py`: consulta, validação mínima e PDF de Imóveis.
- `src/repositorio.py`: repositório de arquivos e MongoDB.
- `src/publicador_evento.py`: evento local JSONL, **não** Kafka/RabbitMQ.
- `schemas/v1/`: contratos JSON Schema.
- `tests/`: testes offline e mocks de consultas HTTP.

**Não implementado/confirmado:** autenticação de produção, assinatura digital, contratos jurídicos, barramento real de eventos, disponibilidade da API externa e integração de Automotivo. O PDF é informativo e não constitui contrato.

## Demonstração sugerida (5 minutos)

1. Abrir `/docs` e mostrar `/api/saude`.
2. Colar `exemplos/credcasa_proposta_exemplo.json` em `POST /api/documentos/credcasa`.
3. Mostrar `documento_id`, evento e baixar o PDF.
4. Repetir com `exemplos/finops_consulta_exemplo.json` em `POST /api/documentos/finops`.
5. Consultar os metadados e explicar que os adaptadores isolam os outros grupos.
6. Rodar `pytest -q` e mostrar os testes.

## Atualização corretiva v1.3.1

Esta entrega corrige o GET de metadados, a máscara de CPF/CNPJ nos PDFs, a validação de datas, o escape de texto no FinOps e os contratos Swagger de FinOps/CredCasa. Inclui testes de regressão e tabela de equivalência Juros/FinOps em `docs/arquitetura.md`.

**Windows (PowerShell):**
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn src.app:app --reload
```
Abra `http://127.0.0.1:8000/docs`. Sem `MONGODB_URI`, os metadados são gravados em JSON local. O teste automatizado não comprova integração com servidores reais.


## Integração Juros offline (v1.4.0)
Veja [INTEGRACAO_JUROS_SEM_API_PUBLICA.md](INTEGRACAO_JUROS_SEM_API_PUBLICA.md).
