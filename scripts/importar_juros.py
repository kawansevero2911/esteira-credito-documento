"""Importação offline: python -m scripts.importar_juros caminho/operacao.json"""
import argparse
import json
from pathlib import Path
from src.app import BASE_DIR, create_app
from src.integracao_juros import emitir_juros


def main():
    parser=argparse.ArgumentParser(description='Importar JSON de Juros sem internet ou API pública')
    parser.add_argument('arquivo',type=Path,help='Arquivo .json enviado pelo grupo de Juros')
    parser.add_argument('--storage',type=Path,default=None,help='Diretório para os PDFs e metadados')
    args=parser.parse_args()
    if not args.arquivo.is_file() or args.arquivo.suffix.lower()!='.json':
        parser.error('Informe um arquivo .json existente')
    dados=json.loads(args.arquivo.read_text(encoding='utf-8'))
    app=create_app(storage_dir=args.storage,imprimir_eventos=False)
    # Reutiliza exatamente a rota/validação e persistência da API, sem iniciar servidor.
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        response=client.post('/api/documentos/juros',json=dados)
    if response.status_code != 201:
        raise SystemExit(f'Erro {response.status_code}: {response.text}')
    print(json.dumps(response.json(),ensure_ascii=False,indent=2))
    print('Documento gerado. Abra o servidor e consulte /api/documentos/{documento_id}/pdf')

if __name__=='__main__':
    main()
