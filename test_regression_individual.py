#!/usr/bin/env python
"""
Teste de regressão: validar que processamento individual de produtos continua funcionando
"""

import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from produtos.models import ProdutoAutomatico, OrigemProduto, StatusExtracao
from produtos.scraper import processar_produto_automatico

print("\n" + "="*70)
print("TESTE DE REGRESSÃO: Processamento Individual de Produtos")
print("="*70)

# Criar um produto de teste
print("\n✅ Criando produto de teste...")
produto_teste = ProdutoAutomatico.objects.create(
    link_afiliado='https://www.mercadolivre.com.br/test',
    origem=OrigemProduto.AUTOMATICO,
    ativo=True,
    status_extracao=StatusExtracao.PENDENTE,
)

print(f"   Produto ID: {produto_teste.id}")
print(f"   Link: {produto_teste.link_afiliado}")
print(f"   Status: {produto_teste.status_extracao}")

# Tentar processar (vai falhar porque a URL é fake, mas não deve dar erro de threading)
print("\n⏳ Processando produto (esperado: falhar na extração, mas sem erro de threading)...")

try:
    resultado = processar_produto_automatico(produto_teste)
    
    # Recarregar para ver resultado
    produto_teste.refresh_from_db()
    
    print(f"\n✅ Processamento completou sem erro de threading!")
    print(f"   Resultado: {resultado}")
    print(f"   Status final: {produto_teste.status_extracao}")
    print(f"   Erro: {produto_teste.erro_extracao[:60] if produto_teste.erro_extracao else 'Nenhum'}")
    print(f"   Falhas: {produto_teste.falhas_consecutivas}")
    
    # Validar que não há erro de asyncio/threading
    if 'asyncio' in str(produto_teste.erro_extracao).lower():
        print(f"\n❌ ERRO: Problema de asyncio detectado!")
        sys.exit(1)
    
    if 'thread' in str(produto_teste.erro_extracao).lower():
        print(f"\n❌ ERRO: Problema de threading detectado!")
        sys.exit(1)
    
    print(f"\n✅ Nenhum erro de asyncio/threading!")
    
except Exception as e:
    print(f"\n❌ ERRO ao processar: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    # Cleanup
    produto_teste.delete()
    print(f"\n🧹 Produto de teste deletado")

print("\n" + "="*70)
print("✅ TESTE DE REGRESSÃO: PASSOU")
print("="*70 + "\n")
