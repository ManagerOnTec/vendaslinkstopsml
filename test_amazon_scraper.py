#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para validar o scraper Amazon especializado.
Teste os dois links problemáticos mencionados:
1. https://amzn.to/4sEGjin - Estava extraindo título como HTML/accessibility text
2. https://amzn.to/4lMCDZp - Estava faltando preço e imagem
"""

import os
import sys
import django
from pprint import pprint
import io

# Force UTF-8 encoding for output
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.scraper import extrair_dados_produto
from produtos.detector_plataforma import DetectorPlataforma

def test_amazon_links():
    """
    Testa a extracao de dados dos dois links Amazon problematicos.
    """
    test_links = [
        ("https://amzn.to/4sEGjin", "Link 1 - Estava extraindo HTML como titulo"),
        ("https://amzn.to/4lMCDZp", "Link 2 - Estava faltando preco e imagem"),
    ]
    
    for url, descricao in test_links:
        print("\n" + "="*80)
        print(f"[TESTE] {descricao}")
        print(f"URL: {url}")
        print("="*80)
        
        # Detectar plataforma
        plataforma = DetectorPlataforma.detectar(url)
        print(f"\n[OK] Plataforma detectada: {plataforma}")
        
        if plataforma != 'amazon':
            print(f"[ERRO] Esperava 'amazon', recebeu '{plataforma}'")
            continue
        
        # Extrair dados
        print("\n[PROC] Extraindo dados...")
        try:
            dados = extrair_dados_produto(url)
            
            print("\n[RESULTADOS]:")
            print("-" * 80)
            
            # Verificar cada campo
            campos_criticos = {
                'titulo': 'Titulo do produto',
                'preco': 'Preco',
                'imagem_url': 'URL da imagem',
                'descricao': 'Descricao',
                'plataforma': 'Plataforma'
            }
            
            for campo, descricao in campos_criticos.items():
                if campo in dados:
                    valor = dados[campo]
                    
                    # Verificar se valor é valido
                    if valor and str(valor).strip():
                        # Truncar valores longos para exibicao
                        display_value = valor if len(str(valor)) < 100 else str(valor)[:97] + "..."
                        print(f"  [OK] {descricao:20s}: {display_value}")
                        
                        # Validacoes especificas
                        if campo == 'titulo':
                            if '<' in str(valor) or 'aria-label' in str(valor) or 'DisclosureTriggered' in str(valor):
                                print(f"      [AVISO] Titulo pode conter HTML ou accessibility text!")
                        elif campo == 'preco':
                            if 'R$' not in str(valor):
                                print(f"      [INFO] Preco sem formatacao R$")
                        elif campo == 'imagem_url':
                            if 'http' not in str(valor):
                                print(f"      [AVISO] URL de imagem parece invalida!")
                    else:
                        print(f"  [VAZIO] {descricao:20s}: [VAZIO]")
                else:
                    print(f"  [NAOEXISTE] {descricao:20s}: [NAO ENCONTRADO]")
            
            # Exibir status geral
            print("\n" + "-" * 80)
            status_extracao = dados.get('status_extracao', 'desconhecido')
            motivo = dados.get('motivo', '')
            
            if status_extracao == 'sucesso':
                print(f"[SUCESSO] STATUS: {status_extracao}")
            else:
                print(f"[FALHA] STATUS: {status_extracao}")
                if motivo:
                    print(f"   Motivo: {motivo}")
            
        except Exception as e:
            print(f"\n[ERRO] ao extrair: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n")

if __name__ == '__main__':
    print("Iniciando testes do scraper Amazon especializado...\n")
    test_amazon_links()
    print("\n" + "="*80)
    print("[FIM] Testes concluidos!")
    print("="*80)
