#!/usr/bin/env python
"""
🧪 TESTE COMPLETO - Mercado Livre + Shopee
Valida que ambas plataformas funcionam corretamente.
"""
import asyncio
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from produtos.scraper import _extrair_dados_ml, _extrair_dados_shopee

async def testar_ml():
    """Testa extração Mercado Livre"""
    print("\n" + "="*80)
    print("🧪 TESTE 1: MERCADO LIVRE")
    print("="*80)
    
    # URL de teste do ML (PDP tradicional)
    url_ml = "https://www.mercadolivre.com.br/p/MLB3789486313"
    
    print(f"\n📍 Testando URL: {url_ml}")
    print("Por favor aguarde (pode levar até 20 segundos)...\n")
    
    try:
        dados = await _extrair_dados_ml(url_ml)
        
        print("✅ RESULTADO DO MERCADO LIVRE:")
        print(f"   Título: {dados.get('titulo', 'NÃO ENCONTRADO')[:80]}")
        print(f"   Preço: {dados.get('preco', 'NÃO ENCONTRADO')}")
        print(f"   Preço Original: {dados.get('preco_original', '---')}")
        print(f"   URL Final: {dados.get('url_final', 'NÃO ENCONTRADO')[:60]}")
        print(f"   Página Type: {dados.get('page_type', 'DESCONHECIDO')}")
        
        # Validação
        has_titulo = len(dados.get('titulo', '')) > 5
        has_preco = len(dados.get('preco', '')) > 3
        
        status = "✅ SUCESSO" if (has_titulo and has_preco) else "⚠️ PARCIAL"
        print(f"\n{status}")
        
        return has_titulo and has_preco
        
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {str(e)[:100]}")
        return False

async def testar_shopee():
    """Testa extração Shopee"""
    print("\n" + "="*80)
    print("🧪 TESTE 2: SHOPEE")
    print("="*80)
    
    # URL de teste do Shopee
    url_shopee = "https://shopee.com.br/product/371644471/143868093"
    
    print(f"\n📍 Testando URL: {url_shopee}")
    print("Por favor aguarde (pode levar até 20 segundos)...\n")
    
    try:
        dados = await _extrair_dados_shopee(url_shopee)
        
        print("✅ RESULTADO DA SHOPEE:")
        print(f"   Título: {dados.get('titulo', 'NÃO ENCONTRADO')[:80]}")
        print(f"   Preço: {dados.get('preco', 'NÃO ENCONTRADO')}")
        print(f"   Preço Original: {dados.get('preco_original', '---')}")
        print(f"   Imagem: {dados.get('imagem_url', 'NÃO ENCONTRADA')[:60]}")
        
        # Validação
        has_titulo = len(dados.get('titulo', '')) > 5
        has_preco = len(dados.get('preco', '')) > 3
        
        status = "✅ SUCESSO" if (has_titulo and has_preco) else "⚠️ PARCIAL"
        print(f"\n{status}")
        
        return has_titulo and has_preco
        
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {str(e)[:100]}")
        return False

async def main():
    print("\n" + "="*80)
    print("🚀 TESTE COMPLETO - MERCADO LIVRE + SHOPEE")
    print("="*80)
    
    # Testar Mercado Livre
    result_ml = await testar_ml()
    
    # Testar Shopee
    result_shopee = await testar_shopee()
    
    # Sumário
    print("\n" + "="*80)
    print("📋 SUMÁRIO DOS TESTES")
    print("="*80)
    print(f"Mercado Livre: {'✅ FUNCIONANDO' if result_ml else '❌ FALHOU'}")
    print(f"Shopee:        {'✅ FUNCIONANDO' if result_shopee else '❌ FALHOU'}")
    print("="*80 + "\n")
    
    if result_ml and result_shopee:
        print("🎉 AMBAS AS PLATAFORMAS ESTÃO FUNCIONANDO!")
    elif result_ml:
        print("⚠️ ML funcionando, mas Shopee com problema")
    elif result_shopee:
        print("⚠️ Shopee funcionando, mas ML com problema")
    else:
        print("❌ Ambas as plataformas com problema")

if __name__ == '__main__':
    asyncio.run(main())
