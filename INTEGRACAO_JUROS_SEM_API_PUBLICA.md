# Integração Juros → Documentos sem API pública

## Opção recomendada: troca de arquivo JSON (offline)
1. Grupo Juros exporta o JSON **integral** de cada operação (como o exemplo `exemplos/juros_operacao_completa.json`).
2. Envia o arquivo por WhatsApp, e-mail, Drive, pendrive ou pasta compartilhada da equipe. **Não precisa instalar nossa API, abrir portas ou alterar o código de Juros.**
3. Nosso grupo salva, por exemplo, `recebidos/OP-2026-0001.json` e, na pasta do projeto, executa:

```powershell
py -m pip install -r requirements.txt
py -m scripts.importar_juros recebidos/OP-2026-0001.json
```

4. O importador usa o mesmo pipeline da rota `POST /api/documentos/juros` internamente: valida, gera PDF, salva metadados e registra evento. Os resultados ficam em `storage/pdfs`, `storage/documentos` e `storage/eventos` (ou MongoDB, se `MONGODB_URI` estiver configurada).

## Opção 2: POST local, quando o grupo de Juros estiver no mesmo computador

```powershell
py -m uvicorn src.app:app --reload --host 127.0.0.1
curl.exe -X POST http://127.0.0.1:8000/api/documentos/juros -H "Content-Type: application/json" --data-binary "@exemplos/juros_operacao_completa.json"
```

Swagger local: http://127.0.0.1:8000/docs. `127.0.0.1` não é acessível de outros computadores. Para envio remoto em tempo real sem API pública, seria preciso VPN privada, túnel autenticado ou fila compartilhada; **o modo arquivo evita isso**.

## Contrato
- JSON original com `identificador`, `estado`, `definicao.sistema`, `taxa`, `cliente`, `entrada` e `simulacoes`.
- Preservar ambas as simulações `SAC` e `PRICE`, inclusive os cronogramas e demonstrativos. O PDF mostra ambas, indicando qual foi definida.
- Taxas de Juros são percentuais (1.85 = 1,85%), não frações como no FinOps (0.0185).
- CPF é mascarado no PDF; não modificar dados de origem.
- Não recalculamos juros, IOF, CET ou parcelas; reproduzimos valores recebidos.
- Dados enviados pelo grupo podem conter CPF: compartilhar por canal privado e restringir acesso aos arquivos.

## Limites
- O exemplo é uma **amostra fornecida pelo grupo**, não uma operação real conciliada.
- O schema exige campos mínimos e valida datas dos vencimentos; não verifica coerência financeira nem autentica o remetente do arquivo.
- PDFs são salvos em disco, MongoDB é opcional para metadados.
- Sem API pública não há POST remoto direto para `localhost`; a entrega offline precisa de um arquivo ou de uma rede privada.
