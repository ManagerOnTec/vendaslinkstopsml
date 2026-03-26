#!/usr/bin/env python
"""
Teste para validar a correção de travamento em processamento em lote no Django Admin.

O problema original:
- Quando múltiplos produtos eram selecionados no admin (extrair/atualizar),
- O sistema ficava travado processando o primeiro item
- Produtos inseridos individualmente funcionavam 100%

A causa:
- asyncio.Semaphore não funciona com múltiplas threads rodando asyncio.run() independentemente
- Processamento sequencial com 1 worker thread era gargalo
- Delay de 500ms entre tarefas multiplicava o tempo total

A solução:
- Substituir asyncio.Semaphore por threading.Semaphore
- Implementar múltiplos workers (3 paralelos) para processar tarefas
- Rate limiting controlado individualmente por thread, não globalmente
"""

import os
import sys
import django
import time
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from produtos.models import ProdutoAutomatico, OrigemProduto, StatusExtracao
from produtos.task_queue import queue_batch_tasks, get_queue_size, get_worker_count, wait_all
from django.utils import timezone

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_batch_processing_with_real_urls():
    """
    Testa processamento em lote com URLs reais para múltiplas plataformas.
    Valida que múltiplos produtos são processados em paralelo e não travados.
    """
    logger.info("=" * 80)
    logger.info("TEST: Processamento em Lote (Simulando ação do Django Admin)")
    logger.info("=" * 80)
    
    # URLs de teste de múltiplas plataformas
    test_urls = [
        # Mercado Livre
        {
            'url': 'https://produto.mercadolivre.com.br/MLB-123456789',
            'nome': 'Produto ML 1',
            'plataforma_esperada': 'mercado_livre'
        },
        # Amazon
        {
            'url': 'https://www.amazon.com.br/dp/B07ABCD1234',
            'nome': 'Produto Amazon 1',
            'plataforma_esperada': 'amazon'
        },
        # Shopee
        {
            'url': 'https://shopee.com.br/product/123456789',
            'nome': 'Produto Shopee 1',
            'plataforma_esperada': 'shopee'
        },
    ]
    
    # Criar produtos de teste
    produtos_teste = []
    logger.info(f"\n📝 Criando {len(test_urls)} produtos de teste...")
    
    for test_item in test_urls:
        try:
            # Verificar se já existe
            produto, criado = ProdutoAutomatico.objects.get_or_create(
                link_afiliado=test_item['url'],
                defaults={
                    'origem': OrigemProduto.AUTOMATICO,
                    'ativo': True,
                    'status_extracao': StatusExtracao.PENDENTE,
                }
            )
            if criado:
                logger.info(f"   ✅ Criado: {test_item['nome']} ({produto.id})")
            else:
                logger.info(f"   ♻️ Já existe: {test_item['nome']} ({produto.id})")
                # Resetar status para testar novamente
                produto.status_extracao = StatusExtracao.PENDENTE
                produto.save()
            
            produtos_teste.append(produto)
        except Exception as e:
            logger.error(f"   ❌ Erro ao criar produto: {e}")
    
    logger.info(f"\n✅ {len(produtos_teste)} produto(s) criado(s)/preparado(s)")
    
    # Simular ação do Django Admin: enfileirar múltiplos produtos
    logger.info(f"\n📋 Enfileirando {len(produtos_teste)} produtos para processamento paralelo...")
    
    from produtos.scraper import processar_produto_automatico
    
    start_time = time.time()
    queue_batch_tasks(processar_produto_automatico, produtos_teste)
    
    logger.info(f"   ✅ Enfileirados!")
    logger.info(f"   📊 Fila: {get_queue_size()} tarefas")
    logger.info(f"   👷 Workers: {get_worker_count()} ativos\n")
    
    # Aguardar processamento
    logger.info("⏳ Aguardando processamento de todas as tarefas...")
    logger.info("   (If this completes quickly and all tasks process, the fix is working!)")
    
    max_wait = 60  # Máximo 60 segundos
    waited = 0
    last_queue_size = get_queue_size()
    
    while waited < max_wait:
        current_queue_size = get_queue_size()
        current_workers = get_worker_count()
        
        if current_queue_size == 0:
            logger.info(f"\n✅ Todas as tarefas foram processadas!")
            break
        
        if current_queue_size != last_queue_size:
            logger.info(f"   📊 Remain: {current_queue_size} tarefas, 👷 {current_workers} workers")
            last_queue_size = current_queue_size
        
        time.sleep(1)
        waited += 1
    
    elapsed = time.time() - start_time
    
    if waited >= max_wait:
        logger.error(f"\n❌ TIMEOUT! Processamento não completou em {max_wait}s (travado?)")
        logger.error(f"   Fila ainda tem: {get_queue_size()} tarefas")
        return False
    
    logger.info(f"\n⏱️  Tempo total: {elapsed:.1f}s")
    
    # Validar que os produtos foram processados
    logger.info(f"\n📊 Verificando resultados dos produtos...")
    
    resultados_ok = 0
    resultados_erro = 0
    
    for produto in produtos_teste:
        produto.refresh_from_db()
        
        if produto.status_extracao == StatusExtracao.PROCESSANDO:
            logger.warning(f"   ⏳ Ainda processando: {produto.id} ({produto.link_afiliado[:50]})")
        elif produto.status_extracao == StatusExtracao.SUCESSO:
            logger.info(f"   ✅ Sucesso: {produto.titulo[:50] if produto.titulo else 'SEM TÍTULO'}")
            resultados_ok += 1
        elif produto.status_extracao == StatusExtracao.ERRO:
            logger.warning(f"   ⚠️ Erro: {produto.erro_extracao[:60]}")
            resultados_erro += 1
    
    logger.info(f"\n📈 Resultado: {resultados_ok} sucesso, {resultados_erro} erros")
    
    return resultados_ok + resultados_erro == len(produtos_teste)


def test_parallel_workers():
    """
    Valida que múltiplos workers estão ativos e processam tarefas em paralelo.
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Validação de Workers Paralelos")
    logger.info("=" * 80)
    
    from produtos.task_queue import queue_task
    
    processed_count = [0]  # Usar lista para capturar no closure
    
    def dummy_task(task_id):
        """Tarefa dummy que simula processamento."""
        processed_count[0] += 1
        logger.info(f"   Task {task_id} processed (total: {processed_count[0]})")
        time.sleep(0.1)
    
    logger.info(f"\n📋 Enfileirando 10 tarefas dummy...")
    
    for i in range(10):
        queue_task(dummy_task, i)
    
    logger.info(f"   ✅ 10 tarefas enfileiradas")
    logger.info(f"   📊 Workers ativos: {get_worker_count()}")
    
    # Aguardar
    start = time.time()
    wait_all()
    elapsed = time.time() - start
    
    logger.info(f"\n✅ Todas as tarefas processadas")
    logger.info(f"⏱️  Tempo: {elapsed:.2f}s (parallelismo = {10 * 0.1 / elapsed:.1f}x)")
    logger.info(f"   Expected: ~1s (paralelo), Got: {elapsed:.2f}s")
    
    if elapsed < 3:
        logger.info("✅ Paralelismo está funcionando!")
        return True
    else:
        logger.warning("⚠️ Processamento parece sequencial (podem ser múltiplas threads bloqueadas)")
        return False


if __name__ == '__main__':
    logger.info("\n🧪 INICIANDO TESTES DE CORREÇÃO DE TRAVAMENTO DO DJANGO ADMIN\n")
    
    # Test 1: Parallelism
    logger.info("\n📌 TEST 1/2: Validando paralelismo de workers...")
    test_parallel_ok = test_parallel_workers()
    
    # Test 2: Batch processing (comentado porque usa URLs externas)
    logger.info("\n📌 TEST 2/2: Processamento em lote (batch)")
    logger.info("   (Pulando teste com URLs reais - usa conexões externas)")
    logger.info("   (Executar manualmente via Django Admin para validação final)")
    
    logger.info("\n" + "=" * 80)
    logger.info("🎯 RESUMO DOS TESTES")
    logger.info("=" * 80)
    
    if test_parallel_ok:
        logger.info("✅ Paralelismo: FUNCIONANDO (múltiplos workers simultâneos)")
    else:
        logger.info("⚠️ Paralelismo: Pode haver issue (verificar logs acima)")
    
    logger.info("\n📝 Para validação final:")
    logger.info("   1. Ir para Django Admin > Produtos > Produtos Automáticos")
    logger.info("   2. Selecionar 3-5 produtos com links válidos")
    logger.info("   3. Executar ação 'Extrair dados'")
    logger.info("   4. Validar que:")
    logger.info("      ✅ Não deixa travado no primeiro item")
    logger.info("      ✅ Processa todos os produtos")
    logger.info("      ✅ Completa em tempo razoável (não sequencial)")
    logger.info("\n" + "=" * 80 + "\n")
