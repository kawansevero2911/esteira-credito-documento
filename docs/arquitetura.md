# Arquitetura — Grupo 6

## Objetivo
Receber informações estruturadas de operações de crédito, validar contratos JSON, gerar documentos PDF, persistir metadados e publicar notificação de documento gerado.

## Fluxo
1. API FastAPI recebe JSON local ou um ID para consulta de serviço externo.
2. Adaptador de origem faz GET (FinOps/CredCasa) quando necessário; **não faz POST em sistemas de terceiros**.
3. JSON Schema verifica campos mínimos; a validação não substitui as regras financeiras dos outros grupos.
4. ReportLab gera PDF informativo, sem recalcular juros, score ou decisão.
5. Repositório persiste metadados (arquivos JSON por padrão; MongoDB se configurado); PDF em disco.
6. Publicador registra `documento.gerado` em `storage/eventos/eventos.jsonl`.
7. GET permite recuperar metadados e baixar PDF pelo UUID.

## Dependências
Python, FastAPI, jsonschema Draft 2020-12, ReportLab, httpx, pytest e pymongo opcional. MongoDB via Docker Compose opcional.

## Segurança e limitações
- IDs de documentos aceitam somente UUID canônico na leitura de arquivos.
- Consultas externas usam URL base fixa por configuração e timeout.
- Sem autenticação/controle de acesso: adequado apenas para protótipo acadêmico em ambiente controlado. Dados pessoais devem ser fictícios em demonstrações.
- CredCasa: schema mínimo do JSON de exemplo; requer validação com ID real antes de declarar integração ao vivo.
- FinOps: GETs testados com mocks e payload offline; comunicação com instância real deve ser testada à parte.
- Event bus é simulado por arquivo; não há entrega distribuída garantida.
- MongoDB não é obrigatório para rodar; a conexão é validada ao iniciar quando habilitada.

## Revisão técnica v1.3.1 — 13/11/2026

### Recursos e problemas resolvidos
| Recurso | Problema que resolve |
|---|---|
| FastAPI | Expõe endpoints e contrato OpenAPI/Swagger para os outros grupos |
| jsonschema + FormatChecker | Rejeita documentos incompatíveis, incluindo datas ISO inválidas onde há `format: date` |
| ReportLab | Produz PDF informativo a partir de dados já calculados pelas origens |
| httpx | Consulta somente leitura de FinOps e CredCasa, com timeout e tratamento de erros |
| Protocols (Python) | Separam armazenamento e publicação do processo de negócio |
| pymongo | Permite persistir metadados no MongoDB quando configurado |
| Docker Compose | Facilita subir um MongoDB local opcional para testes |
| pytest | Automatiza testes de validação, API, PDFs e integrações simuladas |

### Equivalência entre Juros e FinOps
| Conceito | Juros | FinOps |
|---|---|---|
| Taxa mensal de 1,85% | `taxa.taxaFinalMes: 1.85` (percentual) | `condicoesFinanceiras.taxaJuros: 0.0185` (fração) |
| CET anual de 30,89% | `simulacoes.PRICE.cet.anualPercentual: 30.89` | `cet.anual: 0.3089` |
| Valor da parcela | `simulacoes.PRICE.cronograma[].valor` | `parcelas[].valorParcela` |
| Amortização | `simulacoes.PRICE.cronograma[].amortizacao` | `parcelas[].amortizacao` |
| Vencimento | `simulacoes.PRICE.cronograma[].vencimento` | `parcelas[].vencimento` |

Os números acima são os exemplos fornecidos pelos grupos, não cálculos realizados pelo módulo de documentos.

### Correções efetivas nesta versão
- O GET de metadados expõe `tipo_documento`, `origem`, `quantidade_parcelas` e `versao_schema` quando presentes.
- CPF e CNPJ são mascarados nos três tipos de PDF. Os dados de origem permanecem inalterados.
- O JSON Schema usa `FormatChecker`, para datas marcadas com `format: date`.
- Textos dinâmicos do PDF FinOps são escapados antes de criar parágrafos ReportLab.
- Os quatro endpoints de integração têm modelos de resposta e documentação de erros no Swagger; POSTs offline incluem exemplos.
- O identificador consultado no FinOps é codificado na URL.
- Metadados e eventos registram versão `v1` do schema, origem e tipo de documento.

### Limites ainda existentes (não declarar concluídos)
- O fluxo de validação → PDF → repositório → evento ainda está implementado em três rotinas: operação original, FinOps e CredCasa. Futuro aprimoramento: `AdaptadorDocumento` com registro por tipo, para um processo único.
- Ainda não existe adaptador direto para o JSON de Juros; somente a tabela de equivalência acima.
- O schema original é estrito (`additionalProperties: false`): não aceita Score, Decisão, CET ou IOF adicionais sem nova versão contratual. FinOps e CredCasa usam schemas próprios.
- Não foram realizados testes de comunicação com FinOps, CredCasa, Score, Decisão ou Juros em produção; testes de integração existentes são simulados/offline.
- MongoDB real e barramento real não foram verificados. O evento é registrado em arquivo `.jsonl`.
- Não há autenticação/autorização; utilizar somente com dados fictícios em ambiente de demonstração. A máscara no PDF não substitui segurança de acesso.
- O exemplo CredCasa pode conter `status: APROVADA` e `decisao: ANÁLISE MANUAL`; os dados de origem não são reconciliados automaticamente.
