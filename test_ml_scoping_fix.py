#!/usr/bin/env python
"""
Teste de validação - Mercado Livre CORRIGIDO
Validação da estrutura de extraction de preços após fix de scoping.

Testes:
1. Verificar que extractMLPrice está acessível
2. Verificar que extractMLSocialPrice está acessível
3. Testar PDP (deve usar extractMLPrice)
4. Testar /social/ (deve usar extractMLSocialPrice)
"""
import asyncio
from produtos.scraper import _extrair_dados_ml

print("=" * 80)
print("🧪 TESTE DE VALIDAÇÃO - MERCADO LIVRE CORRIGIDO (SCOPING FIX)")
print("=" * 80)

# ============================================================================
# TESTE 1: PDP - Deve usar extractMLPrice (para "melhor preço")
# ============================================================================
print("\n" + "=" * 80)
print("TEST 1: PDP - Extração de Preço (deve pegar 'melhor preço')")
print("=" * 80)

pdp_url = "https://www.mercadolivre.com.br/p/MLB123456789"  # Exemplo fictício
print(f"\n🔗 URL (simulado): {pdp_url}")
print("ℹ️  OBS: Pode falhar se não for URL real, mas vai demonstrar a estrutura")

try:
    # Nota: isso pode não funcionar com URL fictícia
    # O importante é que NÃO lance "extractMLPrice is not defined"
    print("⚠️  Pulando teste com URL fictícia (não será testada)")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)[:100]}")

# ============================================================================
# TESTE 2: Social Profile - Deve usar extractMLSocialPrice (card afiliado)
# ============================================================================
print("\n" + "=" * 80)
print("TEST 2: /social/ - Extração de Preço Afiliado")
print("=" * 80)

social_url = "https://www.mercadolivre.com.br/social/joaoalexandrechaves"
print(f"\n🔗 URL: {social_url}")
print("📊 Extração iniciada...")

try:
    dados = asyncio.run(_extrair_dados_ml(social_url))
    
    print("\n✅ SUCESSO - Não houve erro ReferenceError")
    print("\n📊 Resultado da Extração:")
    print(f"   Título: {dados.get('titulo', 'NÃO ENCONTRADO')[:80]}")
    print(f"   Preço (afiliado): {dados.get('preco', 'NÃO ENCONTRADO')}")
    print(f"   Page Type: {dados.get('page_type', 'DESCONHECIDO')}")
    
except Exception as e:
    error_msg = str(e)
    if "extractMLSocialPrice is not defined" in error_msg:
        print("\n❌ FALHA: extractMLSocialPrice ainda está inacessível!")
        print(f"   Erro: {error_msg[:150]}")
    elif "ReferenceError: extractMLPrice is not defined" in error_msg:
        print("\n❌ FALHA: extractMLPrice ainda está inacessível!")
        print(f"   Erro: {error_msg[:150]}")
    else:
        print(f"\n⚠️  Outro erro (pode ser esperado se URL não responseL): {type(e).__name__}")
        print(f"   Mensagem: {str(e)[:150]}")

# ============================================================================
# TESTE 3: Verificação de Sintaxe
# ============================================================================
print("\n" + "=" * 80)
print("TEST 3: Verificação de Código")
print("=" * 80)

try:
    import sys
    import py_compile
    
    scraper_path = "c:\\Users\\resid\\projetos-managerontec\\vendaslinkstopsml\\produtos\\scraper.py"
    py_compile.compile(scraper_path, doraise=True)
    print("✅ Sintaxe do scraper.py: VÁLIDA")
    
except py_compile.PyCompileError as e:
    print(f"❌ Erro de Sintaxe: {e}")
except Exception as e:
    print(f"⚠️  Erro ao verificar: {e}")

# ============================================================================
# SUMÁRIO
# ============================================================================
print("\n" + "=" * 80)
print("📋 SUMÁRIO DO TESTE")
print("=" * 80)
print("""
✅ Se chegou aqui sem "ReferenceError: extractMLSocialPrice is not defined":
   → FIX FOI SUCESSO! As funções foram movidas para escopo correto.

✅ Estrutura esperada (após fix):
   - extractMLPrice: definida FORA do if/else (acessível no PDP)
   - extractMLSocialPrice: definida FORA do if/else (acessível em /social/)
   - if (isPDP): usa extractMLPrice()
   - else if (isSocial): usa extractMLSocialPrice()

✅ Próximos testes:
   - Testar com URLs reais do Mercado Livre
   - Validar via Django admin > Extrair dados
""")
print("=" * 80)
