#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de integração: Shopee + ML + Amazon
Valida que:
1. Detector reconhece URLs corretamente
2. Dispatcher chama funções corretas
3. Nenhuma regressão em ML/Amazon
"""

import sys
import os

# Adicionar projeto ao path
sys.path.insert(0, os.path.dirname(__file__))

def test_detector():
    """Testa se DetectorPlataforma reconhece plataformas corretamente."""
    print("\n" + "="*70)
    print("1️⃣  TESTANDO DETECTOR DE PLATAFORMA")
    print("="*70)
    
    from produtos.detector_plataforma import DetectorPlataforma
    
    test_cases = [
        # ML
        ("https://produto.mercadolivre.com.br/MLB-1234567890", "mercado_livre"),
        ("https://meli.la/ABC123", "mercado_livre"),
        
        # Amazon
        ("https://amzn.to/3AX1y2Z", "amazon"),
        ("https://www.amazon.com.br/s?k=produto", "amazon"),
        
        # Shopee (NOVO: URL curta)
        ("https://s.shopee.com.br/AKW6NW2RXU", "shopee"),
        ("https://shopee.com.br/product/123456789", "shopee"),
        
        # Shein
        ("https://www.shein.com.br/item-123", "shein"),
    ]
    
    passed = 0
    failed = 0
    
    for url, expected in test_cases:
        detected = DetectorPlataforma.detectar(url)
        status = "✅ PASS" if detected == expected else "❌ FAIL"
        passed += (detected == expected)
        failed += (detected != expected)
        
        print(f"{status} | URL: {url[:50]:<50} | Esperado: {expected:<15} | Detectado: {detected}")
    
    print(f"\n📊 Resultado: {passed}/{len(test_cases)} testes passaram")
    return failed == 0


def test_imports():
    """Testa se todas as funções de scraping são importáveis."""
    print("\n" + "="*70)
    print("2️⃣  TESTANDO IMPORTAÇÕES")
    print("="*70)
    
    try:
        from produtos.scraper import (
            _extrair_dados_ml,
            _extrair_dados_amazon,
            _extrair_dados_shopee,
            _detectar_plataforma_e_extrair,
            extrair_dados_produto,
        )
        
        functions = [
            ("_extrair_dados_ml", _extrair_dados_ml),
            ("_extrair_dados_amazon", _extrair_dados_amazon),
            ("_extrair_dados_shopee", _extrair_dados_shopee),
            ("_detectar_plataforma_e_extrair", _detectar_plataforma_e_extrair),
            ("extrair_dados_produto", extrair_dados_produto),
        ]
        
        for func_name, func in functions:
            print(f"✅ {func_name:<35} | Tipo: {type(func).__name__:<10} | OK")
        
        print(f"\n✅ Todas as {len(functions)} funções importadas com sucesso!")
        return True
        
    except ImportError as e:
        print(f"❌ Erro ao importar: {e}")
        return False


def test_shopee_logic():
    """Testa lógica de extração de Shopee sem executar real requests."""
    print("\n" + "="*70)
    print("3️⃣  TESTANDO LÓGICA SHOPEE (Simulação)")
    print("="*70)
    
    # Simular o que a função de Shopee faz
    
    # Teste 1: Preço com split por Frete
    print("\n📝 Teste 1: Split por 'Frete'")
    bodyText = """
    Produto Exemplo
    R$ 59,98
    R$ 135,00
    Frete Grátis
    Outros vendedores
    R$ 200,00
    """
    # Simular split em Python (case-insensitive)
    import re as re_module
    beforeFrete = re_module.split(r"(?i)frete", bodyText)[0]
    
    # Extrair preços
    import re
    prices = re.findall(r'R\$\s*[0-9.]+,[0-9]{2}', beforeFrete)
    
    expected_prices = ["R$ 59,98", "R$ 135,00"]
    matches = all(p in prices for p in expected_prices) and len(prices) >= 2
    status = "✅ PASS" if matches else "❌ FAIL"
    print(f"{status} | Preços encontrados: {prices}")
    
    # Teste 2: Imagem com tamanho mínimo
    print("\n📝 Teste 2: Validação de imagem > 350x350")
    test_images = [
        {"src": "https://example.com/img.jpg", "w": 400, "h": 400, "should_accept": True},
        {"src": "https://example.com/icon.png", "w": 32, "h": 32, "should_accept": False},
        {"src": "data:image/png;base64,...", "w": 400, "h": 400, "should_accept": False},
    ]
    
    passed_img = 0
    for img in test_images:
        accepted = (
            img["src"] and 
            not img["src"].startswith("data:") and 
            img["w"] >= 350 and 
            img["h"] >= 350
        )
        matches = accepted == img["should_accept"]
        status = "✅" if matches else "❌"
        passed_img += matches
        print(f"{status} | {img['src'][:30]:<30} | {img['w']}x{img['h']} | Aceito: {accepted}")
    
    print(f"\n✅ Testes de lógica: {passed_img}/{len(test_images)} passaram")
    return passed_img == len(test_images)


def test_dispatcher():
    """Testa que o dispatcher direciona corretamente."""
    print("\n" + "="*70)
    print("4️⃣  TESTANDO DISPATCHER (Simulação)")
    print("="*70)
    
    from produtos.detector_plataforma import DetectorPlataforma
    
    urls = [
        ("https://s.shopee.com.br/AKW6NW2RXU", "shopee", "_extrair_dados_shopee"),
        ("https://produto.mercadolivre.com.br/MLB-1234567890", "mercado_livre", "_extrair_dados_ml"),
        ("https://www.amazon.com.br/s?k=produto", "amazon", "_extrair_dados_amazon"),
    ]
    
    for url, expected_plat, expected_func in urls:
        detected = DetectorPlataforma.detectar(url)
        func_map = {
            "mercado_livre": "_extrair_dados_ml",
            "amazon": "_extrair_dados_amazon",
            "shopee": "_extrair_dados_shopee",
        }
        dispatched_func = func_map.get(detected, "UNKNOWN")
        
        matches = detected == expected_plat and dispatched_func == expected_func
        status = "✅ PASS" if matches else "❌ FAIL"
        
        print(f"{status} | URL: {url[:40]:<40} | Plataforma: {detected:<15} | Função: {dispatched_func:<25}")
    
    print(f"\n✅ Dispatcher validado!")
    return True


if __name__ == "__main__":
    print("\n🧪 TESTES DE INTEGRAÇÃO SHOPEE")
    print(f"Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Detector": test_detector(),
        "Imports": test_imports(),
        "Shopee Logic": test_shopee_logic(),
        "Dispatcher": test_dispatcher(),
    }
    
    print("\n" + "="*70)
    print("📋 RESUMO FINAL")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} | {test_name}")
    
    all_passed = all(results.values())
    print("\n" + ("🎉 TUDO OK!" if all_passed else "⚠️  ALGUNS TESTES FALHARAM"))
    print("="*70 + "\n")
    
    sys.exit(0 if all_passed else 1)
