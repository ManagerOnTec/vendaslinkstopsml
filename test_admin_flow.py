#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste completo: simulate admin save com produto Amazon.
Valida o fluxo: URL -> Deteccao -> Extracao -> Salvo no BD
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.models import ProdutoAutomatico, StatusExtracao
from produtos.scraper import processar_produto_automatico
from django.utils import timezone

def test_admin_flow():
    """
    Simula um salvamento de produto no admin.
    """
    print("\n" + "="*80)
    print("[TESTE] Fluxo Completo - Admin Save >> Extracao >> BD")
    print("="*80)
    
    # URL do teste
    url_teste = "https://amzn.to/4sEGjin"
    
    print(f"\n[1] Criando produto Amazon com URL: {url_teste[:40]}...")
    
    # Criar ou atualizar produto
    produto, criado = ProdutoAutomatico.objects.get_or_create(
        link_afiliado=url_teste,
        defaults={
            'ativo': True,
            'titulo': 'TEMP',
            'preco': '0',
        }
    )
    
    print(f"[2] Chamando processar_produto_automatico()...")
    
    try:
        # Isso simula o que acontece quando salva no admin
        processar_produto_automatico(produto)
        
        # Recarregar do BD para ver os dados atualizados
        produto.refresh_from_db()
        
        print(f"\n[RESULTADOS]:")
        print("-" * 80)
        print(f"  Titulo:              {produto.titulo}")
        print(f"  Preco:               {produto.preco}")
        print(f"  Preco Original:      {produto.preco_original}")
        print(f"  Imagem URL:          {produto.imagem_url}")
        print(f"  Categoria:           {produto.categoria}")
        print(f"  Plataforma:          {produto.plataforma}")
        print(f"  Status Extracao:     {produto.status_extracao}")
        print(f"  Falhas Consecutivas: {produto.falhas_consecutivas}")
        print(f"  Ativo:               {produto.ativo}")
        print(f"  Atualizado em:       {produto.data_atualizacao}")
        print("-" * 80)
        
        # Validacoes
        print(f"\n[VALIDACOES]:")
        validacoes = {
            'Titulo nao vazio': bool(produto.titulo) and len(produto.titulo) > 5,
            'Titulo sem HTML': '<' not in (produto.titulo or ''),
            'Preco formatado': 'R$ ' in (produto.preco or ''),
            'Imagem URL valida': produto.imagem_url and 'http' in produto.imagem_url,
            'Plataforma é amazon': produto.plataforma == 'amazon',
            'Status é SUCESSO': produto.status_extracao == StatusExtracao.SUCESSO,
            'Falhas zeradas': produto.falhas_consecutivas == 0,
            'Produto ativo': produto.ativo,
        }
        
        top = 0
        for validacao, resultado in validacoes.items():
            emoji = "[OK]" if resultado else "[FALHA]"
            print(f"  {emoji} {validacao}")
            if resultado:
                top += 1
        
        print(f"\n  Total: {top}/{len(validacoes)} passou")
        
        if top == len(validacoes):
            print("\n[SUCESSO] Fluxo completo funcionando!")
            return True
        else:
            print("\n[AVISO] Alguns testes falharam")
            return False
            
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    resultado = test_admin_flow()
    print("\n" + "="*80)
    sys.exit(0 if resultado else 1)
