"""
Script para testar a extração e processamento automático de categoria.
Execute com: python test_categoria.py
"""
import os
import django
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

# Configurar logging para ver tudo
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from produtos.models import ProdutoAutomatico, Categoria
from produtos.scraper import processar_produto_automatico

print("=" * 80)
print("TESTE DE EXTRAÇÃO E CRIAÇÃO AUTOMÁTICA DE CATEGORIA")
print("=" * 80)

# Input do link
link_teste = input("\n📍 Cole um link do Mercado Livre para testar: ").strip()

if not link_teste:
    print("❌ Link não fornecido!")
    exit(1)

print("\n" + "=" * 80)

# Contar categorias antes
categorias_antes = Categoria.objects.count()
print(f"📊 Categorias no banco ANTES: {categorias_antes}")

# Criar ProdutoAutomatico de teste
print(f"\n🔧 Criando ProdutoAutomatico com link: {link_teste}")
produto = ProdutoAutomatico.objects.create(
    link_afiliado=link_teste,
    ativo=True
)
print(f"✅ ProdutoAutomatico criado com ID: {produto.id}")

print("\n" + "=" * 80)
print("🔄 PROCESSANDO PRODUTO (extração e criação de categoria)...")
print("=" * 80)

# Processar
resultado = processar_produto_automatico(produto)

print("\n" + "=" * 80)
print("📋 RESULTADO DA EXTRAÇÃO")
print("=" * 80)

# Recarregar do banco
produto.refresh_from_db()

print(f"\n✅ Status: {produto.get_status_extracao_display()}")
print(f"📝 Título: {produto.titulo}")
print(f"💰 Preço: {produto.preco}")
print(f"🏷️  Categoria: {produto.categoria.nome if produto.categoria else '❌ NENHUMA'}")
print(f"📷 Imagem: {produto.imagem_url[:60]}..." if produto.imagem_url else "📷 Imagem: Nenhuma")

# Contar categorias depois
categorias_depois = Categoria.objects.count()
novas_categorias = categorias_depois - categorias_antes
print(f"\n📊 Categorias no banco DEPOIS: {categorias_depois}")
print(f"🆕 Novas categorias criadas: {novas_categorias}")

if produto.categoria:
    print(f"\n✅ SUCESSO! Categoria atribuída: {produto.categoria}")
else:
    print(f"\n❌ FALHA! Nenhuma categoria foi atribuída!")

if produto.erro_extracao:
    print(f"\n⚠️  Erro registrado: {produto.erro_extracao}")

print("\n" + "=" * 80)
