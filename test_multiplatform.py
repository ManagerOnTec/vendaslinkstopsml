#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste completo: múltiplas plataformas (ML + Amazon) sendo processadas.
Valida fila de tarefas e rate limiting.
"""

import os, sys, django, logging, time
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
django.setup()

from produtos.models import ProdutoAutomatico, StatusExtracao
from produtos.scraper import processar_produto_automatico
from produtos.task_queue import queue_batch_tasks, get_queue_size, wait_all

def test_multi_platform_batch():
    """Teste com múltiplas plataformas simultâneas."""
    
    print("\n" + "="*80)
    print("[TESTE] Processamento em lote Multi-Plataforma via Fila")
    print("="*80)
    
    urls = [
        ("https://amzn.to/4sEGjin", "Amazon - Cadeira"),
        ("https://amzn.to/4lMCDZp", "Amazon - Microsoft 365"),
    ]
    
    print(f"\n[ETAPA 1] Criando {len(urls)} produtos no BD...")
    produtos = []
    for url, descricao in urls:
        produto, criado = ProdutoAutomatico.objects.get_or_create(
            link_afiliado=url,
            defaults={'ativo': True, 'titulo': 'TEMP', 'preco': '0'}
        )
        produtos.append(produto)
        status = "CRIADO" if criado else "EXISTENTE"
        print(f"  [{status}] {descricao}: {url}")
    
    print(f"\n[ETAPA 2] Enfileirando {len(produtos)} produtos para processamento assíncrono...")
    start_time = time.time()
    
    # Usar a fila para enfileirar tarefas
    queue_batch_tasks(processar_produto_automatico, produtos)
    
    print(f"  Tamanho da fila: {get_queue_size()}")
    
    print(f"\n[ETAPA 3] Aguardando conclusão...")
    sucesso = wait_all()
    elapsed = time.time() - start_time
    
    if sucesso:
        print(f"  ✓ Todas as tarefas completadas em {elapsed:.2f}s")
    else:
        print(f"  × Timeout ou erro ao aguardar tarefas")
    
    print(f"\n[ETAPA 4] Validando resultados...")
    
    for i, produto in enumerate(produtos):
        produto.refresh_from_db()
        print(f"\n  Produto {i+1}:")
        print(f"    URL: {produto.link_afiliado}")
        print(f"    Titulo: {produto.titulo[:50] if produto.titulo else '(vazio)'}")
        print(f"    Preco: {produto.preco or '(vazio)'}")
        print(f"    Plataforma: {produto.plataforma}")
        print(f"    Status: {produto.status_extracao}")
        print(f"    Falhas: {produto.falhas_consecutivas}")
        
        # Validação
        validacoes_ok = (
            produto.titulo and len(produto.titulo) > 5 and
            'R$' in (produto.preco or '') and
            produto.imagem_url and
            produto.plataforma and
            produto.status_extracao
        )
        
        print(f"    Resultado: {'✓ SUCESSO' if validacoes_ok else '✗ INCOMPLETO'}")
    
    print("\n" + "="*80)
    print("[FIM] Teste multi-plataforma concluído")
    print("="*80 + "\n")

if __name__ == '__main__':
    test_multi_platform_batch()
