#!/usr/bin/env python
"""
Script de teste para validar scrapers Shopee e Amazon (VERSÃO REFATORADA)
Execução: python manage.py shell < test_scrapers.py
"""

import asyncio
import logging
from produtos.scraper import _extrair_dados_shopee, _extrair_dados_amazon

# Configurar logging detalhado
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_shopee():
    """Teste do scraper Shopee refatorado"""
    print("\n" + "="*100)
    print("🛍️  TESTE SHOPEE (Refatorado - Seletores Diretos)")
    print("="*100)
    
    url_shopee = "https://s.shopee.com.br/2LToEqKjC"
    
    try:
        print(f"\n📍 Testando URL: {url_shopee}")
        print("⏳ Aguardando extração (pode levar 20-30 segundos)...")
        
        resultado = await _extrair_dados_shopee(url_shopee)
        
        print("\n✅ RESULTADO SHOPEE:")
        print(f"   Título: {resultado.get('titulo', '❌ NÃO ENCONTRADO')[:80]}")
        print(f"   Preço:  {resultado.get('preco', '❌ NÃO ENCONTRADO')}")
        print(f"   Imagem: {resultado.get('imagem_url', '❌ NÃO ENCONTRADA')[:80]}")
        print(f"   Categoria: {resultado.get('categoria', '❌ NÃO ENCONTRADA')}")
        print(f"   Descrição: {resultado.get('descricao', '❌ NÃO ENCONTRADA')[:80]}")
        
        # Validação
        campos_populados = sum([
            bool(resultado.get('titulo')),
            bool(resultado.get('preco')),
            bool(resultado.get('imagem_url')),
        ])
        
        print(f"\n📊 RESULTADO: {campos_populados}/3 campos extraídos com sucesso")
        
        if campos_populados == 3:
            print("✅ SHOPEE: TESTE PASSOU - Todos os campos extraídos!")
        elif campos_populados >= 2:
            print("⚠️  SHOPEE: TESTE PARCIAL - Alguns campos faltando")
        else:
            print("❌ SHOPEE: TESTE FALHOU - Não conseguiu extrair dados")
        
        return resultado
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE SHOPEE: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_amazon():
    """Teste do scraper Amazon refatorado"""
    print("\n" + "="*100)
    print("📦 TESTE AMAZON (Refatorado - Seletores Diretos)")
    print("="*100)
    
    url_amazon = "https://amzn.to/486LO0W"
    
    try:
        print(f"\n📍 Testando URL: {url_amazon}")
        print("⏳ Aguardando extração (pode levar 30-40 segundos)...")
        
        resultado = await _extrair_dados_amazon(url_amazon)
        
        print("\n✅ RESULTADO AMAZON:")
        print(f"   Título: {resultado.get('titulo', '❌ NÃO ENCONTRADO')[:80]}")
        print(f"   Preço:  {resultado.get('preco', '❌ NÃO ENCONTRADO')}")
        print(f"   Imagem: {resultado.get('imagem_url', '❌ NÃO ENCONTRADA')[:80]}")
        print(f"   Descrição: {resultado.get('descricao', '❌ NÃO ENCONTRADA')[:80]}")
        
        # Validação
        campos_populados = sum([
            bool(resultado.get('titulo')),
            bool(resultado.get('preco')),
            bool(resultado.get('imagem_url')),
        ])
        
        print(f"\n📊 RESULTADO: {campos_populados}/3 campos extraídos com sucesso")
        
        if campos_populados == 3:
            print("✅ AMAZON: TESTE PASSOU - Todos os campos extraídos!")
        elif campos_populados >= 2:
            print("⚠️  AMAZON: TESTE PARCIAL - Alguns campos faltando")
        else:
            print("❌ AMAZON: TESTE FALHOU - Não conseguiu extrair dados")
        
        return resultado
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE AMAZON: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Executar todos os testes"""
    print("\n" + "="*100)
    print("🧪 INICIANDO TESTES DOS SCRAPERS REFATORADOS")
    print("="*100)
    print("\nMudanças implementadas:")
    print("  • Shopee: seletores simples (h1, spans com R$, meta tags)")
    print("  • Amazon: prioridade #productTitle, #landingImage, #feature-bullets")
    print("  • Ambos: wait_for_selector() + networkidle para carregamento completo")
    print("  • Timeout aumentado: 50-60s para URLs encurtadas (amzn.to)")
    
    shopee_result = await test_shopee()
    amazon_result = await test_amazon()
    
    print("\n" + "="*100)
    print("📋 RESUMO DOS TESTES")
    print("="*100)
    
    if shopee_result:
        shopee_ok = shopee_result.get('titulo') and shopee_result.get('preco') and shopee_result.get('imagem_url')
        print(f"Shopee: {'✅ PASSOU' if shopee_ok else '⚠️ PARCIAL'}")
    else:
        print("Shopee: ❌ FALHOU")
    
    if amazon_result:
        amazon_ok = amazon_result.get('titulo') and amazon_result.get('preco') and amazon_result.get('imagem_url')
        print(f"Amazon: {'✅ PASSOU' if amazon_ok else '⚠️ PARCIAL'}")
    else:
        print("Amazon: ❌ FALHOU")
    
    print("="*100)

if __name__ == '__main__':
    asyncio.run(main())

