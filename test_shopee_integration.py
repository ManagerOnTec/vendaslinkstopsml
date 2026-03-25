#!/usr/bin/env python
"""
TESTE DE INTEGRAÇÃO - Validação que Shopee está extraindo preço com estratégia CSS
"""

import asyncio
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

async def test_shopee_extraction():
    """
    Teste que Shopee consegue extrair preço com a estratégia CSS
    Validar:
    1. CSS Selectors Strategy: Primária (deve encontrar preço nas classes Shopee)
    2. Regex Fallback: Secundária (se CSS falhar, regex tenta)
    3. Retorno correto: Deve retornar dict com 'preco' preenchido
    """
    from produtos.scraper import _extrair_dados_shopee
    
    print("\n" + "="*60)
    print("🧪 TESTE DE INTEGRAÇÃO SHOPEE - CSS Selector Strategy")
    print("="*60)
    
    # URL real de Shopee (deve ter preço)
    url_shopee = "https://shopee.com.br/Luminaria-Redonda-LED-em-Arandela-de-parede-p-16950897-5bde5e1aefeb3f048f7c1c72e62e7ba0"
    
    try:
        print(f"\n📍 URL teste: {url_shopee}")
        print("\n🔄 Executando extração Shopee (com estratégia CSS -> Regex)...")
        
        dados = await _extrair_dados_shopee(url_shopee)
        
        print("\n✅ Extração concluída!")
        print(f"\n📊 Dados extraídos:")
        print(f"   Título: {dados.get('titulo', '-')[:60]}...")
        print(f"   Preço: {dados.get('preco', 'NÃO ENCONTRADO')}")
        print(f"   Preço Original: {dados.get('preco_original', '-')}")
        print(f"   Descrição: {dados.get('descricao', '-')[:60]}...")
        print(f"   Imagem URL: {dados.get('imagem_url', 'NÃO ENCONTRADA')[:60]}...")
        
        # Validações
        print("\n🔍 VALIDAÇÕES:")
        
        validacoes = {
            "1. Preço extraído (não vazio)": bool(dados.get('preco')),
            "2. Preço em formato R$ (contém 'R$' ou número)": bool(
                dados.get('preco') and (
                    'R$' in dados.get('preco', '') or 
                    any(c.isdigit() for c in dados.get('preco', ''))
                )
            ),
            "3. Título extraído": bool(dados.get('titulo')),
            "4. Imagem URL extraída": bool(dados.get('imagem_url')),
        }
        
        for validacao, resultado in validacoes.items():
            status = "✅" if resultado else "❌"
            print(f"   {status} {validacao}")
        
        # Resultado final
        preco_ok = validacoes["1. Preço extraído (não vazio)"]
        if preco_ok:
            print("\n" + "="*60)
            print("✅ SHOPEE COM ESTRATÉGIA CSS FUNCIONANDO!")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("⚠️  SHOPEE SEM PREÇO - Revisar estratégia CSS")
            print("="*60)
            return False
            
    except Exception as e:
        print(f"\n❌ ERRO durante extração: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_shopee_functions_directly():
    """
    Teste das funções helper direto para validar lógica CSS
    """
    from produtos.scraper import _extrair_preco_shopee_simples
    from playwright.async_api import async_playwright
    
    print("\n" + "="*60)
    print("🧪 TESTE DIRETO - Funções de Helper")
    print("="*60)
    
    url = "https://shopee.com.br/Luminaria-Redonda-LED-em-Arandela-de-parede-p-16950897-5bde5e1aefeb3f048f7c1c72e62e7ba0"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            print(f"\n📍 Navegando para: {url}")
            await page.goto(url, wait_until="load", timeout=30000)
            
            print("\n✅ Página carregada! Testando estratégias de extração...")
            
            # Teste do helper de preço
            print("\n🔍 Testando _extrair_preco_shopee_simples()...")
            preco_atual, preco_original = await _extrair_preco_shopee_simples(page)
            
            print(f"   Preço Atual: {preco_atual if preco_atual else 'NÃO ENCONTRADO'}")
            print(f"   Preço Original: {preco_original if preco_original else 'NÃO ENCONTRADO'}")
            
            if preco_atual:
                print("   ✅ Preço foi extraído com sucesso!")
                resultado = True
            else:
                print("   ⚠️  Preço não foi extraído - CSS selectors não funcionaram")
                resultado = False
            
            await browser.close()
            return resultado
            
    except Exception as e:
        print(f"\n❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n" + "="*60)
    print("🚀 VALIDAÇÃO COMPLETA - SHOPEE CSS SELECTOR STRATEGY")
    print("="*60)
    
    # Teste 1: Funções diretas
    print("\n[FASE 1] Testando funções helper...")
    teste1_ok = await test_shopee_functions_directly()
    
    # Teste 2: Integração completa
    print("\n[FASE 2] Testando integração completa...")
    teste2_ok = await test_shopee_extraction()
    
    # Resultado final
    print("\n" + "="*60)
    print("📋 RESULTADO FINAL")
    print("="*60)
    print(f"   Fase 1 (Helper funções): {'✅ PASSOU' if teste1_ok else '⚠️  COM PROBLEMAS'}")
    print(f"   Fase 2 (Integração): {'✅ PASSOU' if teste2_ok else '⚠️  COM PROBLEMAS'}")
    
    if teste1_ok and teste2_ok:
        print("\n✅ TODAS AS VALIDAÇÕES PASSARAM!")
        print("   Shopee está extraindo preço via CSS Strategy corretamente!")
        return 0
    else:
        print("\n⚠️  Algumas validações falharam - revisar logs acima")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
