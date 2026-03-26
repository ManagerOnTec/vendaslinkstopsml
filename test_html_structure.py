#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para verificar o conteúdo do HTML
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

# Informações básicas
print(f"Status: {response.status_code}")
print(f"Tamanho HTML: {len(content)}")

# Procurar por "Plataforma:" no HTML
if 'Plataforma:' in content:
    print(f"\nEncontrado 'Plataforma:' no HTML")
    pos = content.find('Plataforma:')
    print(f"   Posicao: {pos}")
    start = max(0, pos - 100)
    end = min(len(content), pos + 300)
    snippet = content[start:end]
    print(f"\n--- Contexto (100 chars antes e 300 depois) ---")
    print(snippet)
    print("--- Fim contexto ---\n")
else:
    print(f"\nNAO encontrado 'Plataforma:' no HTML")
    
    # Verificar usando split para encontrar "Plataforma"
    if 'Plataforma' in content:
        print("\nMas ENCONTRADO 'Plataforma' (sem dois-pontos)")
        parts = content.split('Plataforma')
        print(f"Encontrado {len(parts)-1} vezes")
        
        # Mostrar alguns contextos
        for i, part in enumerate(parts[1:4]):
            print(f"\n--- Ocorrencia {i+1} ---")
            print(part[:200])
    
    # Procurar por variações
    if 'funnel' in content:
        print("\n\nEncontrado 'funnel' (icone do filtro)")
        pos = content.find('funnel')
        print(f"Posicao: {pos}")
        print(content[max(0, pos-100):pos+200])

