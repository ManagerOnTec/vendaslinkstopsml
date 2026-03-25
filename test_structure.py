#!/usr/bin/env python
"""
🧪 TESTE SIMPLIFICADO - Mercado Livre + Shopee
Valida estrutura de código (não necessita URLs válidas)
"""
import re

def test_ml_structure():
    """Verifica se ML está estruturado corretamente"""
    print("\n" + "="*80)
    print("✅ TEST 1: MERCADO LIVRE - Estrutura de Código")
    print("="*80)
    
    with open('produtos/scraper.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # Verificar se isSocial é testado PRIMEIRO
    if 'if (isSocial)' in content:
        ml_section = content[content.find('async def _extrair_dados_ml'):content.find('async def _extrair_dados_amazon')]
        if 'if (isSocial)' in ml_section:
            is_social_pos = ml_section.find('if (isSocial)')
            is_pdp_pos = ml_section.find('else if (isPDP)')
            if is_social_pos > 0 and (is_pdp_pos < 0 or is_social_pos < is_pdp_pos):
                checks.append(("✅", "isSocial testado ANTES de isPDP"))
            else:
                checks.append(("❌", "isSocial NÃO está primeiro"))
        else:
            checks.append(("⚠️", "isSocial não encontrado em ML"))
    else:
        checks.append(("❌", "isSocial não definido"))
    
    # Verificar extractMLPrice
    if 'const extractMLPrice = () => {' in content:
        checks.append(("✅", "extractMLPrice() definida"))
    else:
        checks.append(("❌", "extractMLPrice() não definida"))
    
    # Verificar extractMLSocialPrice
    if 'const extractMLSocialPrice = () => {' in content:
        checks.append(("✅", "extractMLSocialPrice() definida"))
    else:
        checks.append(("❌", "extractMLSocialPrice() não definida"))
    
    # Verificar se não há fragmento solto
    if re.search(r"preco = extractMLPrice\(\);\s*'\.ui-pdp-price__second-line'", content):
        checks.append(("❌", "Fragmento solto detectado"))
    else:
        checks.append(("✅", "Nenhum fragmento solto"))
    
    for symbol, msg in checks:
        print(f"   {symbol} {msg}")
    
    ml_ok = all(c[0] == "✅" for c in checks)
    return ml_ok

def test_shopee_structure():
    """Verifica se Shopee está estruturado corretamente"""
    print("\n" + "="*80)
    print("✅ TEST 2: SHOPEE - Estrutura de Código")
    print("="*80)
    
    with open('produtos/scraper.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = []
    
    # Verificar funções simplificadas
    if 'async def _extrair_preco_shopee_simples' in content:
        checks.append(("✅", "_extrair_preco_shopee_simples() definida"))
    else:
        checks.append(("❌", "_extrair_preco_shopee_simples() não definida"))
    
    if 'async def _extrair_imagem_shopee_simples' in content:
        checks.append(("✅", "_extrair_imagem_shopee_simples() definida"))
    else:
        checks.append(("❌", "_extrair_imagem_shopee_simples() não definida"))
    
    # Verificar se está chamando as funções simplificadas
    shopee_section = content[content.find('async def _extrair_dados_shopee'):content.find('async def _extrair_dados_genererico')]
    
    if 'await _extrair_preco_shopee_simples' in shopee_section:
        checks.append(("✅", "Usando _extrair_preco_shopee_simples()"))
    else:
        checks.append(("❌", "NÃO usando _extrair_preco_shopee_simples()"))
    
    if 'await _extrair_imagem_shopee_simples' in shopee_section:
        checks.append(("✅", "Usando _extrair_imagem_shopee_simples()"))
    else:
        checks.append(("❌", "NÃO usando _extrair_imagem_shopee_simples()"))
    
    # Verificar que não há wait_for_function complexo
    if 'prices.length >= 2 && !text.includes' in content:
        checks.append(("⚠️", "Ainda tem lógica complexa de wait_for_function"))
    else:
        checks.append(("✅", "Sem wait_for_function complexo"))
    
    for symbol, msg in checks:
        print(f"   {symbol} {msg}")
    
    shopee_ok = all(c[0] == "✅" for c in checks)
    return shopee_ok

def main():
    print("\n" + "="*80)
    print("🚀 VALIDAÇÃO DE ESTRUTURA - MERCADO LIVRE + SHOPEE")
    print("="*80)
    
    ml_ok = test_ml_structure()
    shopee_ok = test_shopee_structure()
    
    print("\n" + "="*80)
    print("📋 SUMÁRIO")
    print("="*80)
    print(f"Mercado Livre: {'✅ CORRETO' if ml_ok else '❌ PROBLEMA'}")
    print(f"Shopee:        {'✅ CORRETO' if shopee_ok else '❌ PROBLEMA'}")
    print("="*80)
    
    if ml_ok and shopee_ok:
        print("\n✅ AMBAS AS PLATAFORMAS ESTRUTURADAS CORRETAMENTE!")
        print("   • ML: Social-first pattern, sem fragmentos soltos")
        print("   • Shopee: Usando estratégia simples")
        return 0
    else:
        print("\n❌ PROBLEMAS NA ESTRUTURA")
        return 1

if __name__ == '__main__':
    exit(main())
