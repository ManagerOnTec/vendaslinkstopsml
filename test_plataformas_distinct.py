#!/usr/bin/env python
"""
Script para testar se plataformas estão renderizadas corretamente
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.test import Client
import re

client = Client()

# Teste: verificar plataformas no HTML
print("✅ Teste: Verificar plataformas no HTML")
print("-" * 50)
response = client.get('/')
content = response.content.decode('utf-8')

print(f"Tamanho do HTML: {len(content)} caracteres")
print(f"Status da resposta: {response.status_code}")

# Procurar por "Plataforma:" no HTML
if 'Plataforma:' in content:
    print("✅ Filtro 'Plataforma:' encontrado no HTML")
    
    # Contar quantas vezes "Plataforma:" aparece
    count_plataforma = content.count('Plataforma:')
    print(f"   Aparições de 'Plataforma:': {count_plataforma}")
    
    if count_plataforma > 1:
        print("⚠️  PROBLEMA DETECTADO: Filtro de plataforma aparece mais de uma vez!")
    else:
        print("✅ Filtro aparece apenas uma vez (correto)")
    
    # Procurar por padrão ?plataforma=X no HTML
    pattern = r'plataforma=([a-z_]+)'
    matches = re.findall(pattern, content)
    
    print(f"\nURLs com parâmetro 'plataforma' encontradas: {len(matches)}")
    if matches:
        print(f"Plataformas: {sorted(set(matches))}")
        from collections import Counter
        counts = Counter(matches)
        print(f"\nDetalhes:")
        for plat, count in sorted(counts.items()):
            if count > 1:
                print(f"  ⚠️  {plat}: {count}x")
            else:
                print(f"  ✅ {plat}: {count}x")
else:
    print("❌ Filtro 'Plataforma:' NÃO encontrado no HTML")
    
    # Debug: procurar por qualquer menção de plataforma
    if 'plataforma' in content.lower():
        print("   Mas encontrei menção de 'plataforma' (minúscula) no HTML")
        count = content.lower().count('plataforma')
        print(f"   Total de menções: {count}")
    else:
        print("   E nem encontrei nenhuma menção de 'plataforma'")
        
        # Verificar se há dados no contexto
        print("\n   DEBUG: Procurando por 'amazon' (um produto que existe)")
        if 'amazon' in content:
            print("   ✅ Encontrado 'amazon' no HTML")
        else:
            print("   ❌ Não encontrado 'amazon' no HTML")
