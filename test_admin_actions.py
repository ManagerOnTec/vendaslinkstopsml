"""
Teste de diagnóstico das ações admin extract/re-extract.
Simula o comportamento das ações do admin para identificar o problema.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.models import ProdutoAutomatico
from produtos.scraper import processar_produto_automatico
from produtos.task_queue import queue_batch_tasks, get_queue_size, get_worker_count
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_individual_add():
    """Test 1: Adicionar um produto individualmente (simula save_model)"""
    print("\n" + "="*60)
    print("TEST 1: ADICIONAR PRODUTO INDIVIDUALMENTE")
    print("="*60)
    
    # Criar produto de teste
    from produtos.models import OrigemProduto
    
    test_url = "https://www.mercadolivre.com.br/teclado-mecanico-rgb/p/123"
    
    # Limpar produto de teste anterior se existir
    ProdutoAutomatico.objects.filter(link_afiliado=test_url).delete()
    
    produto = ProdutoAutomatico(
        link_afiliado=test_url,
        origem=OrigemProduto.AUTOMATICO
    )
    
    print(f"✓ Criado produto: {produto.link_afiliado}")
    print(f"  Status inicial: {produto.status_extracao}")
    
    # Processar SINCRONAMENTE (como em save_model)
    print("\n→ Chamando processar_produto_automatico() SINCRONAMENTE...")
    start = time.time()
    try:
        result = processar_produto_automatico(produto)
        elapsed = time.time() - start
        
        print(f"✓ Processamento concluído em {elapsed:.2f}s")
        print(f"  Resultado: {result}")
        print(f"  Título: {produto.titulo or 'NÃO EXTRAÍDO'}")
        print(f"  Preço: {produto.preco or 'NÃO EXTRAÍDO'}")
        print(f"  Status: {produto.status_extracao}")
        print(f"  Erro: {produto.erro_extracao or 'Nenhum'}")
        return result
    except Exception as e:
        elapsed = time.time() - start
        print(f"✗ Erro após {elapsed:.2f}s: {type(e).__name__}: {e}")
        return False


def test_batch_action():
    """Test 2: Usar a ação de batch (simula admin action)"""
    print("\n" + "="*60)
    print("TEST 2: AÇÃO ADMIN BATCH (extract)")
    print("="*60)
    
    # Pegar um produto existente ou criar um
    from produtos.models import OrigemProduto, StatusExtracao
    
    test_url = "https://www.mercadolivre.com.br/teclado-mecanico-rgb/p/456"
    
    # Limpar e criar novo
    ProdutoAutomatico.objects.filter(link_afiliado=test_url).delete()
    
    produto = ProdutoAutomatico.objects.create(
        link_afiliado=test_url,
        origem=OrigemProduto.AUTOMATICO,
        status_extracao=StatusExtracao.PENDENTE
    )
    
    print(f"✓ Criado produto: {produto.id} - {produto.link_afiliado}")
    print(f"  Status inicial: {produto.status_extracao}")
    
    # Enquque para processamento (como em extrair_dados_action)
    print(f"\n→ Enfileirando para processamento com {get_worker_count()} workers...")
    queue_batch_tasks(processar_produto_automatico, [produto])
    print(f"✓ Tarefa enfileirada. Fila tem {get_queue_size()} itens")
    
    # Aguardar processamento
    print(f"\n→ Aguardando processamento (máx 30 segundos)...")
    for i in range(30):
        time.sleep(1)
        queue_size = get_queue_size()
        worker_count = get_worker_count()
        
        # Recarregar do BD
        produto.refresh_from_db()
        
        print(f"   [{i+1:2d}s] Status: {produto.status_extracao:12s} | Fila: {queue_size:2d} | Workers: {worker_count} | Título: {(produto.titulo or 'VAZIO')[:30]}")
        
        # Se completou, parar
        if produto.status_extracao in ['sucesso', 'erro']:
            break
    
    # Verificar resultado final
    print(f"\n✓ Resultado final:")
    print(f"  Status: {produto.status_extracao}")
    print(f"  Título: {produto.titulo or 'NÃO EXTRAÍDO'}")
    print(f"  Preço: {produto.preco or 'NÃO EXTRAÍDO'}")
    print(f"  Erro: {produto.erro_extracao or 'Nenhum'}")
    
    return bool(produto.titulo)


def main():
    print("\n🔧 TESTE DE DIAGNÓSTICO - AÇÕES ADMIN")
    print("=" * 60)
    
    # Test 1
    resultado_individual = test_individual_add()
    
    time.sleep(2)
    
    # Test 2
    resultado_batch = test_batch_action()
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO")
    print("="*60)
    print(f"Individual (sincrone):  {'✅ FUNCIONA' if resultado_individual else '❌ PROBLEMA'}")
    print(f"Batch (async):          {'✅ FUNCIONA' if resultado_batch else '❌ PROBLEMA'}")
    
    if not resultado_batch:
        print("\n⚠️  PROBLEMA IDENTIFICADO: Ações admin (async) não estão funcionando!")
        print("   Possíveis causas:")
        print("   1. Workers não estão processando corretamente")
        print("   2. Exceções estão sendo silenciosamente capturadas")
        print("   3. Database locking/transaction issue")
        print("   4. Problema com asyncio.run() em threads")


if __name__ == '__main__':
    main()
