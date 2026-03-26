#!/usr/bin/env python
"""
Script para debug do template - procurar pela seção de filtro
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.test import Client

client = Client()

# Requisição
response = client.get('/')
content = response.content.decode('utf-8')

# Procurar por "Limpar filtros" (deve estar antes do filtro de plataformas)
limpar_pos = content.find('Limpar filtros')
if limpar_pos != -1:
    print("✅ Encontrado 'Limpar filtros'")
    
    # Procurar pelo que vem depois
    section = content[limpar_pos:limpar_pos+1500]
    print("\nHTML após 'Limpar filtros':")
    print("=" * 60)
    print(section)
    print("=" * 60)
    
    if 'Plataforma:' in section:
        print("\n✅ 'Plataforma:' encontrado LOGO APÓS 'Limpar filtros'")
    else:
        print("\n❌ 'Plataforma:' NÃO encontrado na seção esperada")
else:
    print("❌ 'Limpar filtros' não encontrado no HTML")
    
    # Debug: Procurar por qualquer coisa que indique a estrutura
    if 'page-header' in content:
        print("✅ Encontrado 'page-header' no HTML")
        pos = content.find('page-header')
        print(content[pos:pos+500])
    else:
        print("❌ 'page-header' tidak encontrado")
