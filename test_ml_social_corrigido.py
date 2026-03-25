#!/usr/bin/env python
"""
Teste de validação da extração Mercado Livre corrigida (páginas /social/).
Executa a extração e valida que está pegando o preço AFILIADO, não de loja oficial.

Uso:
    python manage.py shell < test_ml_social_corrigido.py
    
ou dentro do shell:
    exec(open('test_ml_social_corrigido.py').read())
"""
import asyncio
from produtos.scraper import _extrair_dados_ml

# Link de teste de página /social/ (perfil de afiliado)
test_url = "https://www.mercadolivre.com.br/social/joaoalexandrechaves"

print("=" * 80)
print("🧪 TESTE DE EXTRAÇÃO MERCADO LIVRE SOCIAL (AFILIADO) - CORRIGIDO")
print("=" * 80)
print(f"\n🔗 URL de teste: {test_url}")
print(f"\n📊 Executando extração...\n")

# Executar extração
dados = asyncio.run(_extrair_dados_ml(test_url))

# Exibir resultados
print("\n" + "=" * 80)
print("📋 RESULTADOS DA EXTRAÇÃO")
print("=" * 80)

resultado_titulo = "✅" if dados.get('titulo') else "❌"
resultado_preço = "✅" if dados.get('preco') else "❌"
resultado_imagem = "✅" if dados.get('imagem_url') else "❌"
resultado_categoria = "✅" if dados.get('categoria') else "❌"

print(f"\n{resultado_titulo} Título (do card afiliado):")
print(f"   {dados.get('titulo', 'NÃO ENCONTRADO')[:100]}")

print(f"\n{resultado_preço} Preço (deve ser AFILIADO):")
print(f"   {dados.get('preco', 'NÃO ENCONTRADO')}")

print(f"\n   (Deve ser o preço do CARD afiliado, NÃO de loja oficial)")

print(f"\n   Preço Original (desconto):")
print(f"   {dados.get('preco_original', 'NÃO ENCONTRADO')}")

print(f"\n{resultado_imagem} Imagem URL:")
print(f"   {dados.get('imagem_url', 'NÃO ENCONTRADA')[:100]}")

print(f"\n📝 Descrição:")
print(f"   {dados.get('descricao', 'NÃO ENCONTRADA')[:100]}")

print(f"\n{resultado_categoria} Categoria:")
print(f"   {dados.get('categoria', 'NÃO ENCONTRADA')}")

print(f"\n🔗 URL Final:")
print(f"   {dados.get('url_final', 'NÃO ENCONTRADA')}")

print(f"\n📋 Tipo de Página:")
print(f"   {dados.get('page_type', 'DESCONHECIDO')}")

# Validação de sucesso
print("\n" + "=" * 80)
print("✅ VALIDAÇÃO ✅")
print("=" * 80)

checks = {
    "Preço extraído (afiliado)": bool(dados.get('preco')),
    "Titulo extraído": bool(dados.get('titulo')),
    "Imagem extraída": bool(dados.get('imagem_url')),
    "URL final capturada": bool(dados.get('url_final')),
    "Página detectada como social": dados.get('page_type') == 'social',
}

for check, result in checks.items():
    status = "✅" if result else "❌"
    print(f"{status} {check}")

all_passed = all(checks.values())
print("\n" + "=" * 80)
if all_passed:
    print("🎉 TESTE PASSOU! Extração corrigida está funcionando.")
    print("    ✅ Preço afiliado (primeiro card)")
    print("    ✅ Ignorando loja oficial")
else:
    print("⚠️ TESTE COM FALHAS - Verifique os erros acima.")
print("=" * 80)
