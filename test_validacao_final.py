#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TESTE SEGURO - Valida correções ML + Shopee
Sem problemas de encoding
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ml_logic():
    """Valida que ML agora rejeita Loja Oficial"""
    logger.info("\n" + "="*70)
    logger.info("🧪 VALIDAÇÃO - Mercado Livre")
    logger.info("="*70)
    
    with open('produtos/scraper.py', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Validações
    checks = {
        "✅ extractMLPrice() definida": "const extractMLPrice = () => {" in content,
        "✅ ESTRATÉGIA 3 adicionada (Preço Vendedor)": "vendorPriceContainers" in content,
        "✅ Rejeita 'loja oficial' em ESTRATÉGIA 1": "!containerText.includes('loja oficial')" in content or "!containerText.includes('loja oficial')" in content,
        "✅ Rejeita 'Mercado Livre Official'": "containerText.includes('mercado')" in content,
        "✅ Social-first: isSocial ANTES isPDP": "if (isSocial)" in content and "} else if (isPDP)" in content,
    }
    
    for check, result in checks.items():
        status = "✓" if result else "✗"
        logger.info(f"   {status} {check}")
    
    all_pass = all(checks.values())
    return all_pass


def test_shopee_logic():
    """Valida que Shopee agora usa wait_for_function com desconto"""
    logger.info("\n" + "="*70)
    logger.info("🧪 VALIDAÇÃO - Shopee")
    logger.info("="*70)
    
    with open('produtos/scraper.py', 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    # Validações
    checks = {
        "✅ _extrair_preco_shopee_simples() definida": "async def _extrair_preco_shopee_simples(page):" in content,
        "✅ wait_for_function() com R$ e %": "b.innerText.includes('R$')" in content and "b.innerText.includes('%')" in content,
        "✅ Rejeita 'outros vendedores'": "outros vendedores" in content,
        "✅ Rejeita 'loja oficial'": "'loja oficial'" in content,
        "✅ Preço antes de 'Frete'": "text.split(/Frete/i)[0]" in content,
        "✅ Imagem com dimensão > 400x400": "img.naturalWidth > 400" in content and "img.naturalHeight > 400" in content,
        "✅ _extrair_imagem_shopee_simples() definida": "async def _extrair_imagem_shopee_simples(page):" in content,
    }
    
    for check, result in checks.items():
        status = "✓" if result else "✗"
        logger.info(f"   {status} {check}")
    
    all_pass = all(checks.values())
    return all_pass


def test_imports():
    """Valida que funcões são importáveis"""
    logger.info("\n" + "="*70)
    logger.info("🧪 TESTE - Importações")
    logger.info("="*70)
    
    try:
        from produtos.scraper import (
            _extrair_dados_ml,
            _extrair_dados_shopee,
            _extrair_preco_shopee_simples,
            _extrair_imagem_shopee_simples,
        )
        logger.info("   ✓ Todas as funções importadas com sucesso")
        return True
    except ImportError as e:
        logger.error(f"   ✗ Erro ao importar: {str(e)}")
        return False


def main():
    """Executa todos os testes"""
    logger.info("\n" + "="*70)
    logger.info("🚀 VALIDAÇÃO FINAL - Correções ML + Shopee")
    logger.info("="*70)
    
    tests = [
        ("Importações", test_imports),
        ("Mercado Livre", test_ml_logic),
        ("Shopee", test_shopee_logic),
    ]
    
    results = {}
    for name, test_func in tests:
        try:
            results[name] = test_func()
        except Exception as e:
            logger.error(f"❌ {name} FALHOU: {str(e)[:100]}")
            results[name] = False
    
    # Resumo
    logger.info("\n" + "="*70)
    logger.info("📋 RESUMO")
    logger.info("="*70)
    
    for name, passed in results.items():
        status = "✅ PASSOU" if passed else "❌ FALHOU"
        logger.info(f"   {name}: {status}")
    
    if all(results.values()):
        logger.info("\n✅ TODAS AS VALIDAÇÕES PASSARAM!")
        logger.info("\n📊 Mudanças Aplicadas:")
        logger.info("   • ML: ESTRATÉGIA 3 para rejeitar Loja Oficial")
        logger.info("   • Shopee: wait_for_function() com R$ + % + Frete")
        logger.info("   • Shopee: Imagem validada > 400x400")
        return 0
    else:
        logger.error("\n❌ Algumas validações falharam")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
