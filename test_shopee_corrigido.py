#!/usr/bin/env python
"""
Teste de validação da extração Shopee corrigida.
Executa a extração do link fornecido e valida os resultados.

Uso:
    python manage.py shell < test_shopee_corrigido.py
    
ou dentro do shell:
    exec(open('test_shopee_corrigido.py').read())
"""
import asyncio
from produtos.scraper import _extrair_dados_shopee

# Link de teste fornecido pelo usuário
test_url = "https://s.shopee.com.br/AKW6NW2RXU"

print("=" * 80)
print("🧪 TESTE DE EXTRAÇÃO SHOPEE CORRIGIDA")
print("=" * 80)
print(f"\n🔗 URL de teste: {test_url}")
print(f"\n📊 Executando extração...\n")

# Executar extração
dados = asyncio.run(_extrair_dados_shopee(test_url))

# Exibir resultados
print("\n" + "=" * 80)
print("📋 RESULTADOS DA EXTRAÇÃO")
print("=" * 80)

resultado_preço = "✅" if dados.get('preco') else "❌"
resultado_imagem = "✅" if dados.get('imagem_url') else "❌"
resultado_titulo = "✅" if dados.get('titulo') else "❌"
resultado_preco_original = "✅" if dados.get('preco_original') else "❌"

print(f"\n{resultado_titulo} Título:")
print(f"   {dados.get('titulo', 'NÃO ENCONTRADO')[:100]}")

print(f"\n{resultado_preço} Preço Atual:")
print(f"   {dados.get('preco', 'NÃO ENCONTRADO')}")

print(f"\n{resultado_preco_original} Preço Original:")
print(f"   {dados.get('preco_original', 'NÃO ENCONTRADO')}")

print(f"\n{resultado_imagem} Imagem URL:")
print(f"   {dados.get('imagem_url', 'NÃO ENCONTRADA')[:100]}")

print(f"\n📝 Descrição:")
print(f"   {dados.get('descricao', 'NÃO ENCONTRADA')[:100]}")

print(f"\n🏷️ Categoria:")
print(f"   {dados.get('categoria', 'NÃO ENCONTRADA')}")

print(f"\n🔗 URL Final:")
print(f"   {dados.get('url_final', 'NÃO ENCONTRADA')}")

# Validação de sucesso
print("\n" + "=" * 80)
print("✅ VALIDAÇÃO ✅")
print("=" * 80)

checks = {
    "Preço extraído": bool(dados.get('preco')),
    "Imagem extraída": bool(dados.get('imagem_url')),
    "Título extraído": bool(dados.get('titulo')),
    "URL final capturada": bool(dados.get('url_final')),
}

for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check}")

all_passed = all(checks.values())
print("\n" + "=" * 80)
if all_passed:
    print("🎉 TESTE PASSOU! Extração corrigida está funcionando.")
else:
    print("⚠️ TESTE COM FALHAS - Verifique os erros acima.")
print("=" * 80)
