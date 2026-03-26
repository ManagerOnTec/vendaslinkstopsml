#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Debug: Salvar HTML em arquivo para análise
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/')
content = response.content.decode('utf-8')

# Salvar em arquivo
with open('debug_output.html', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"HTML salvo em debug_output.html ({len(content)} caracteres)")

# Procurar por section com plataformas
if 'Limpar filtros' in content:
    pos = content.find('Limpar filtros')
    section = content[pos:pos+2000]
    
    with open('seção_filtro.txt', 'w', encoding='utf-8') as f:
        f.write(section)
    
    print("\nSecao após 'Limpar filtros' salva em seção_filtro.txt")
    print(section[:500])
else:
    print("Nao encontrado 'Limpar filtros'")
