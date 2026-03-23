"""
Script de teste para a extração de dados e categoria do scraper.
Execute com: python test_scraper.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.scraper import extrair_dados_produto
import json

# Teste com um link do Mercado Livre
link_teste = input("Cole um link do Mercado Livre para testar: ")

print("\n🔄 Iniciando extração...")
try:
    dados = extrair_dados_produto(link_teste)
    
    print("\n✅ Dados extraídos:")
    print(json.dumps(dados, indent=2, ensure_ascii=False))
    
    if dados.get('categoria'):
        print(f"\n✅ CATEGORIA EXTRAÍDA: {dados['categoria']}")
    else:
        print("\n❌ CATEGORIA NÃO FOI EXTRAÍDA!")
        
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
