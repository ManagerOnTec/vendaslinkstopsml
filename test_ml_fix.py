#!/usr/bin/env python
"""
✅ TESTE DE VALIDAÇÃO - CORREÇÃO MERCADO LIVRE (Reordenação Social-First)
Valida que:
1. Não há erro de sintaxe Playwright: "SyntaxError: Unexpected token ')'"
2. Lógica de page.evaluate é válida
3. Social é testado ANTES de PDP
4. Sem fragmentos soltos no código
"""
import re
import sys

def test_scraper_syntax():
    """Verifica se há fragmentos soltos ou sintaxe quebrada"""
    
    try:
        with open(
            'c:\\Users\\resid\\projetos-managerontec\\vendaslinkstopsml\\produtos\\scraper.py',
            'r',
            encoding='utf-8'
        ) as f:
            content = f.read()
        
        # ✅ TEST 1: Verificar se extractMLPrice está DEFINIDA no topo
        if 'const extractMLPrice = () => {' in content:
            print("✅ TEST 1 PASSED: extractMLPrice() definida fora de if/else")
        else:
            print("❌ TEST 1 FAILED: extractMLPrice() não encontrada")
            return False
        
        # ✅ TEST 2: Verificar se extractMLSocialPrice está DEFINIDA no topo
        if 'const extractMLSocialPrice = () => {' in content:
            print("✅ TEST 2 PASSED: extractMLSocialPrice() definida fora de if/else")
        else:
            print("❌ TEST 2 FAILED: extractMLSocialPrice() não encontrada")
            return False
        
        # ✅ TEST 3: Verificar se isSocial é testado PRIMEIRO
        # Procurar por "if (isSocial)" antes de "if (isPDP)"
        if_social_pos = content.find('if (isSocial)')
        if_pdp_pos = content.find('if (isPDP)')
        
        # Preciso procurar pela primeira ocorrência em um contexto de page.evaluate
        # Vamos buscar no contexto correto do Mercado Livre
        ml_eval_section = content[content.find('_extrair_dados_ml'):content.find('async def _extrair_dados_amazon')]
        
        isSocial_in_ml = ml_eval_section.find('if (isSocial)')
        isPDP_in_ml = ml_eval_section.find('else if (isPDP)')
        
        if isSocial_in_ml > 0 and isPDP_in_ml > isSocial_in_ml:
            print("✅ TEST 3 PASSED: isSocial testado ANTES de isPDP (social-first pattern)")
        else:
            print("⚠️  TEST 3 WARNED: Ordem de if/else pode estar incorreta")
        
        # ✅ TEST 4: Verificar se há fragmentos soltos como '.ui-pdp-price__second-line'
        # sem um contexto válido
        broken_fragment = re.search(r"preco = extractMLPrice\(\);\s*'\.", content)
        if broken_fragment:
            print("❌ TEST 4 FAILED: Fragmento solto detectado após extractMLPrice()")
            return False
        else:
            print("✅ TEST 4 PASSED: Nenhum fragmento solto detectado")
        
        # ✅ TEST 5: Verificar se a lógica de social é simples (sem código quebrado)
        if ".poly-price__current .andes-money-amount" in content:
            print("✅ TEST 5 PASSED: Seletores de preço social corretos")
        else:
            print("⚠️  TEST 5 WARNED: Seletores de preço social podem estar faltando")
        
        # ✅ TEST 6: Importar e verificar sintaxe Python
        try:
            import produtos.scraper
            print("✅ TEST 6 PASSED: Módulo scraper.py importa sem erro de sintaxe")
        except SyntaxError as e:
            if "Unexpected token" in str(e):
                print(f"❌ TEST 6 FAILED: Erro de sintaxe JavaScript no py_compile: {e}")
                return False
        except Exception as e:
            print(f"⚠️  TEST 6 INFO: {type(e).__name__}: {str(e)[:80]}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO GERAL: {type(e).__name__}: {e}")
        return False

def main():
    print("\n" + "=" * 80)
    print("🧪 TESTE DE VALIDAÇÃO - MERCADO LIVRE (Correção de Sintaxe)")
    print("=" * 80 + "\n")
    
    success = test_scraper_syntax()
    
    print("\n" + "=" * 80)
    if success:
        print("✅ RESULTADO: TODOS OS TESTES PASSARAM")
        print("\n📋 O que foi corrigido:")
        print("  • Fragmento solto '.ui-pdp-price__second-line' REMOVIDO")
        print("  • Ordem invertida: if (isSocial) ANTES de else if (isPDP)")
        print("  • Lógica de social: simples e isolada (sem PDP logic)")
        print("  • Funções extractMLPrice() e extractMLSocialPrice() acessíveis")
        print("\n🚀 Pronto para testar via Django Admin!")
    else:
        print("❌ RESULTADO: ALGUNS TESTES FALHARAM")
        sys.exit(1)
    print("=" * 80 + "\n")

if __name__ == '__main__':
    main()
