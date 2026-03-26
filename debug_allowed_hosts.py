#!/usr/bin/env python
"""
Script para debugar ALLOWED_HOSTS em produção no GCP Cloud Run.
Mostra exatamente qual é o valor que está sendo carregado.
"""
import os
import sys

# Simular carregamento de environment vars
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')

from decouple import config, Csv

print("=" * 80)
print("🔍 DEBUG: ALLOWED_HOSTS Configuration")
print("=" * 80)

# 1. Verificar valor bruto da variável de ambiente
raw_value = os.environ.get('ALLOWED_HOSTS', '(não definido)')
print(f"\n1️⃣ ALLOWED_HOSTS (raw environment variable):")
print(f"   Valor: '{raw_value}'")
print(f"   Tipo: {type(raw_value)}")
print(f"   Bytes: {raw_value.encode() if raw_value != '(não definido)' else 'N/A'}")

# 2. Verificar como decouple lê
decouple_value = config("ALLOWED_HOSTS", default="")
print(f"\n2️⃣ ALLOWED_HOSTS (via decouple.config):")
print(f"   Valor: '{decouple_value}'")
print(f"   Tipo: {type(decouple_value)}")
print(f"   Comprimento: {len(decouple_value)} caracteres")

# 3. Verificar como está sendo parseado em settings.py
parsed_list = [s.strip() for s in decouple_value.split(",") if s]
print(f"\n3️⃣ ALLOWED_HOSTS (parsed as list):")
print(f"   Total de hosts: {len(parsed_list)}")
for i, host in enumerate(parsed_list, 1):
    print(f"   [{i}] '{host}' (len={len(host)})")

# 4. Verificar cada host individualmente
print(f"\n4️⃣ Análise individual de cada host:")
for i, host in enumerate(parsed_list, 1):
    print(f"\n   Host #{i}: '{host}'")
    print(f"      - Caracteres: {list(host)}")
    print(f"      - Hex: {host.encode('utf-8').hex()}")
    print(f"      - Tem espaço no início: {host[0] == ' ' if host else False}")
    print(f"      - Tem espaço no final: {host[-1] == ' ' if host else False}")

# 5. Verificar se 'backcountry.s5stratos.com' está na lista
target_host = 'backcountry.s5stratos.com'
print(f"\n5️⃣ Procurando por '{target_host}':")
if target_host in parsed_list:
    print(f"   ✅ ENCONTRADO!")
else:
    print(f"   ❌ NÃO ENCONTRADO!")
    print(f"   Hosts disponíveis:")
    for h in parsed_list:
        print(f"      - {h}")
    
    # Sugerir possível problema
    print(f"\n   💡 Possíveis problemas:")
    print(f"      - O host '{target_host}' não está na variável ALLOWED_HOSTS")
    print(f"      - Há whitespace invisível que não foi removido")
    print(f"      - A variável de ambiente não foi carregada neste deploy")

# 6. Usando Csv cast como em settings.py
csv_parsed = list(config("ALLOWED_HOSTS", default="", cast=Csv()))
print(f"\n6️⃣ ALLOWED_HOSTS (via Csv cast):")
print(f"   Total de hosts: {len(csv_parsed)}")
for i, host in enumerate(csv_parsed, 1):
    print(f"   [{i}] '{host}'")

# 7. DEBUG = False significa produção?
debug_value = config("DEBUG", default=True, cast=bool)
print(f"\n7️⃣ DEBUG setting:")
print(f"   Valor: {debug_value}")
print(f"   Modo: {'DESENVOLVIMENTO' if debug_value else 'PRODUÇÃO'}")

print("\n" + "=" * 80)
