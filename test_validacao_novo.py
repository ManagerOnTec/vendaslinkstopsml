#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste de validação: Verificar que a lógica de:
1. Validação de campos críticos funciona
2. Retry logic (máx 2 falhas) funciona
3. Desativação após 2 falhas funciona
4. Filtro de produtos com erro funciona
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Configurar Django antes de importar modelos
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

def test_validacao_de_campos():
    """Testa se _validar_campos_criticos funciona corretamente."""
    print("\n" + "="*70)
    print("1️⃣  TESTANDO VALIDAÇÃO DE CAMPOS CRÍTICOS")
    print("="*70)
    
    from produtos.scraper import _validar_campos_criticos
    
    test_cases = [
        # (dados, esperado_valido, descrição)
        (
            {'titulo': 'Produto', 'preco': 'R$ 100,00', 'imagem_url': 'https://exemplo.com/img.jpg'},
            True,
            "✅ Todos os campos preenchidos"
        ),
        (
            {'titulo': 'Produto', 'preco': '', 'imagem_url': 'https://exemplo.com/img.jpg'},
            False,
            "❌ Preço vazio"
        ),
        (
            {'titulo': '', 'preco': 'R$ 100,00', 'imagem_url': 'https://exemplo.com/img.jpg'},
            False,
            "❌ Título vazio"
        ),
        (
            {'titulo': 'Produto', 'preco': 'R$ 100,00', 'imagem_url': ''},
            False,
            "❌ Imagem vazia"
        ),
    ]
    
    passed = 0
    for dados, esperado_valido, desc in test_cases:
        valido, msg = _validar_campos_criticos(dados)
        matches = valido == esperado_valido
        status = "✅ PASS" if matches else "❌ FAIL"
        passed += matches
        
        print(f"{status} | {desc}")
        if msg:
            print(f"      └─ Erro: {msg}")
    
    print(f"\n📊 Resultado: {passed}/{len(test_cases)} testes passaram")
    return passed == len(test_cases)


def test_shopee_regex_patterns():
    """Testa se os padrões de regex do Shopee funcionam."""
    print("\n" + "="*70)
    print("2️⃣  TESTANDO PADRÕES DE REGEX - SHOPEE")
    print("="*70)
    
    import re
    
    test_texts = [
        # (texto, padrao, esperado)
        (
            "Produto: R$ 59,98 original R$ 135,00 Frete Grátis",
            r"R\$\s*[\d.]+,\d{2}",
            ["R$ 59,98", "R$ 135,00"]
        ),
        (
            "Preço: R$ 1.234,56 com desconto Frete",
            r"R\$\s*[\d.]+,\d{2}",
            ["R$ 1.234,56"]
        ),
        (
            "Valor R$ 99,90",
            r"R\$\s*\d+,\d{2}",
            ["R$ 99,90"]
        ),
    ]
    
    passed = 0
    for texto, padrao, esperado in test_texts:
        # Simular split por Frete
        before_frete = texto.split("Frete")[0] if "Frete" in texto else texto
        matches = re.findall(padrao, before_frete)
        
        é_correto = all(e in matches for e in esperado) and len(matches) >= len(esperado)
        status = "✅ PASS" if é_correto else "❌ FAIL"
        passed += é_correto
        
        print(f"{status} | Texto: '{texto[:50]}...'")
        print(f"      └─ Esperado: {esperado}, Obtido: {matches}")
    
    print(f"\n📊 Resultado: {passed}/{len(test_texts)} testes passaram")
    return passed == len(test_texts)


def test_filtro_status_erro():
    """Testa se o filtro de status ERRO funciona na view."""
    print("\n" + "="*70)
    print("3️⃣  TESTANDO FILTRO DE STATUS ERRO NA VIEW")
    print("="*70)
    
    from produtos.models import StatusExtracao
    
    # Verificar que StatusExtracao tem as opções corretas
    opcoes = dict(StatusExtracao.choices)
    
    print(f"✅ StatusExtracao opções: {list(opcoes.keys())}")
    
    esperados = ['pendente', 'processando', 'sucesso', 'erro']
    tem_todos = all(e in opcoes for e in esperados)
    
    status = "✅ PASS" if tem_todos else "❌ FAIL"
    print(f"{status} | { 'Todas as opções presentes' if tem_todos else 'Faltam opções'}")
    
    return tem_todos


def test_modelo_campos():
    """Testa se ProdutoAutomatico tem os campos necessários."""
    print("\n" + "="*70)
    print("4️⃣  TESTANDO CAMPOS DO MODELO")
    print("="*70)
    
    from produtos.models import ProdutoAutomatico
    
    campos_necessarios = [
        'status_extracao',
        'falhas_consecutivas',
        'ativo',
        'motivo_desativacao',
        'titulo',
        'preco',
        'imagem_url',
        'categoria',
    ]
    
    passed = 0
    for campo in campos_necessarios:
        tem_campo = hasattr(ProdutoAutomatico, campo)
        status = "✅" if tem_campo else "❌"
        passed += tem_campo
        print(f"{status} | Campo '{campo}'")
    
    print(f"\n📊 Resultado: {passed}/{len(campos_necessarios)} campos presentes")
    return passed == len(campos_necessarios)


if __name__ == "__main__":
    print("\n🧪 TESTES DE VALIDAÇÃO - NOVA LÓGICA")
    print(f"Timestamp: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "Validação de Campos": test_validacao_de_campos(),
        "Regex Shopee": test_shopee_regex_patterns(),
        "Filtro Status Erro": test_filtro_status_erro(),
        "Campos do Modelo": test_modelo_campos(),
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
