# Arquitetura — Estruturação de Documentos

## Responsabilidade

Serviço de suporte da Esteira de Crédito responsável pela validação dos dados recebidos e pela estruturação/emissão de documentos.

## Componentes

- API REST: entrada e saída HTTP.
- Validador: validação contra JSON Schema.
- Processo: orquestração do fluxo.
- Mapeador: conversão do contrato de entrada para o modelo documental.
- Gerador PDF: emissão do documento.
- Repositório: persistência local dos metadados.
- Publicador: registro do evento gerado.

## Princípio de evolução

As interfaces entre componentes são mantidas separadas para permitir a substituição do armazenamento local por uma base orientada a documentos e da publicação local por um barramento compartilhado.
