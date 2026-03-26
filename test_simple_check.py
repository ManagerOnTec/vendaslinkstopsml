#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script simplificado para verificar o filtro no HTML
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.test import Client

client = Client()
response = client.get('/')
content = response.content.decode('utf-8')

# Procurar por "bg-secondary me-2" que é parte do badge de Plataforma:
if 'bg-secondary me-2' in content:
    print("Encontrado 'bg-secondary me-2' badge")
    pos = content.find('bg-secondary me-2')
    context = content[pos-50:pos+300]
    print(context)
    print("\n" + "="*60 + "\n")

# Procurar por "funnel" que é o ícone do filtro
if 'funnel' in content:
    print("Encontrado 'funnel' (icone filtro)")
    pos = content.find('funnel')
    context = content[pos-100:pos+200]
    print(context)
