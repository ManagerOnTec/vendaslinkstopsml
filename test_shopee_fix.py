#!/usr/bin/env python
"""
Teste das correções: Shopee, Mercado Livre e validação com categoria obrigatória
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.scraper import _validar_campos_criticos

print("\n" + "="*70)
print("🧪 TESTES DE VALIDAÇÃO COM CATEGORIA OBRIGATÓRIA")
print("="*70 + "\n")

# ===== TESTE 1: Todos os campos preenchidos =====
print("1️⃣ TESTE: Todos os campos preenchidos")
dados = {
    'titulo': 'Mochila Grande',
    'preco': 'R$ 99,90',
    'imagem_url': 'https://example.com/img.jpg',
    'categoria': 'Bolsas Masculinas',
}
valido, msg = _validar_campos_criticos(dados)
print(f"  Esperado: válido=True")
print(f"  Obtido: válido={valido}, msg='{msg}'")
print(f"  Status: {'✅ PASS' if valido else '❌ FAIL'}\n")

# ===== TESTE 2: Categoria vazia =====
print("2️⃣ TESTE: Categoria vazia (deve falhar)")
dados = {
    'titulo': 'Mochila Grande',
    'preco': 'R$ 99,90',
    'imagem_url': 'https://example.com/img.jpg',
    'categoria': '',
}
valido, msg = _validar_campos_criticos(dados)
print(f"  Esperado: válido=False, msg contém 'Categoria'")
print(f"  Obtido: válido={valido}, msg='{msg}'")
print(f"  Status: {'✅ PASS' if not valido and 'Categoria' in msg else '❌ FAIL'}\n")

# ===== TESTE 3: Preço vazio =====
print("3️⃣ TESTE: Preço vazio (deve falhar)")
dados = {
    'titulo': 'Mochila Grande',
    'preco': '',
    'imagem_url': 'https://example.com/img.jpg',
    'categoria': 'Bolsas Masculinas',
}
valido, msg = _validar_campos_criticos(dados)
print(f"  Esperado: válido=False, msg='Preço não foi encontrado'")
print(f"  Obtido: válido={valido}, msg='{msg}'")
print(f"  Status: {'✅ PASS' if not valido and 'Preço' in msg else '❌ FAIL'}\n")

# ===== TESTE 4: Múltiplos campos vazios =====
print("4️⃣ TESTE: Múltiplos campos vazios (deve falhar no primeiro)")
dados = {
    'titulo': '',
    'preco': '',
    'imagem_url': '',
    'categoria': '',
}
valido, msg = _validar_campos_criticos(dados)
print(f"  Esperado: válido=False (detecta primeiro campo vazio)")
print(f"  Obtido: válido={valido}, msg='{msg}'")
print(f"  Status: {'✅ PASS' if not valido else '❌ FAIL'}\n")

# ===== TESTE 5: Whitespace apenas =====
print("5️⃣ TESTE: Campos com spaces apenas (deve ser tratado como vazio)")
dados = {
    'titulo': '   ',
    'preco': 'R$ 99,90',
    'imagem_url': 'https://example.com/img.jpg',
    'categoria': 'Bolsas',
}
valido, msg = _validar_campos_criticos(dados)
print(f"  Esperado: válido=False (whitespace = empty)")
print(f"  Obtido: válido={valido}, msg='{msg}'")
print(f"  Status: {'✅ PASS' if not valido else '❌ FAIL'}\n")

print("="*70)
print("📋 RESUMO DAS MUDANÇAS")
print("="*70)
print("""
✅ Shopee - Melhorias implementadas:
   • Preço: Novo seletor CSS 'div:has-text("R$") span' em vez de regex
   • Preço: Trata faixa de preço (ex: 39,99 - 43,99) pegando o menor
   • Categoria: Extrair do breadcrumb 'div[class*="breadcrumb"] a'
   • Categoria: Pega o SEGUNDO item (primeira categoria relevante)

✅ Mercado Livre - Melhorias implementadas:
   • Fallback de categoria agora tem mais keywords (mouse, teclado, etc)
   • Fallback acontece ANTES da validação
   • Se não encontrar categoria, validação falha e produto é marcado como ERRO

✅ Validação - Mudanças implementadas:
   • Categoria agora é CAMPO OBRIGATÓRIO
   • Se QUALQUER campo (titulo, preco, imagem_url, categoria) vazio → ERRO
   • Após 2 falhas consecutivas → ativo=False (auto-deactivation)

✅ Fluxo de processamento - Reorganizado assim:
   1. Extrai dados via scraper especializado
   2. Tenta fallback de categoria (keywords)
   3. Valida campos críticos (4 obrigatórios)
   4. Se validação falha → ERRO + falhas_consecutivas++
   5. Se falhas >= 2 → ativo=False (desativa)
   6. Se validação passa → cria categoria + salva como SUCESSO
""")
print("="*70)
print("✅ Testes prontos para execução!\n")
