#!/usr/bin/env python
"""
Script de diagnóstico para verificar se task_queue está funcionando corretamente.
Simula o fluxo de importação com logging detalhado.
"""
import os
import sys
import django
import logging
import time

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from produtos.models import ProdutoAutomatico, OrigemProduto, StatusExtracao
from produtos.task_queue import queue_batch_tasks, get_queue_size, get_worker_count
from django.db import transaction

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_worker_function(produto):
    """Função teste que simula o processamento de um produto."""
    logger.info(f"🔍 TEST START: Processando produto {produto.id}: {produto.link_afiliado[:50]}")
    
    # Simular processamento
    time.sleep(2)
    
    # Atualizar status manualmente para demonstrar que funcionou
    produto.status_extracao = StatusExtracao.SUCESSO
    produto.titulo = f"[TESTE] Título extraído para {produto.id}"
    produto.save(update_fields=['status_extracao', 'titulo'])
    
    logger.info(f"✅ TEST DONE: Produto {produto.id} processado com sucesso")


def main():
    logger.info("="*60)
    logger.info("🧪 TESTE DE DIAGNÓSTICO - TASK QUEUE")
    logger.info("="*60)
    
    # 1. Limpar produtos de teste anteriores
    logger.info("\n1️⃣ Limpando produtos de teste anteriores...")
    deletados = ProdutoAutomatico.objects.filter(
        origem=OrigemProduto.AUTOMATICO,
        link_afiliado__startswith="https://teste-"
    ).delete()
    logger.info(f"   Deletados: {deletados}")
    
    # 2. Criar produtos de teste
    logger.info("\n2️⃣ Criando 3 produtos de teste...")
    produtos_teste = []
    links_teste = [
        "https://teste-11111.com/produto1",
        "https://teste-22222.com/produto2",
        "https://teste-33333.com/produto3",
    ]
    
    with transaction.atomic():
        for link in links_teste:
            produto = ProdutoAutomatico.objects.create(
                link_afiliado=link,
                origem=OrigemProduto.AUTOMATICO,
                ativo=True,
                status_extracao=StatusExtracao.PENDENTE
            )
            produtos_teste.append(produto)
            logger.info(f"   ✓ Criado: {produto.id} - {link}")
    
    logger.info(f"   Total: {len(produtos_teste)} produtos")
    
    # 3. Verificar status inicial
    logger.info("\n3️⃣ Status inicial dos produtos:")
    for p in ProdutoAutomatico.objects.filter(id__in=[p.id for p in produtos_teste]):
        logger.info(f"   Produto {p.id}: status={p.get_status_extracao_display()}, titulo={p.titulo or 'VAZIO'}")
    
    # 4. Enfileirar tarefas
    logger.info("\n4️⃣ Enfileirando produtos para processamento...")
    logger.info(f"   Estado antes: fila_size={get_queue_size()}, workers={get_worker_count()}")
    
    queue_batch_tasks(test_worker_function, produtos_teste)
    
    logger.info(f"   Estado depois: fila_size={get_queue_size()}, workers={get_worker_count()}")
    
    # 5. Aguardar processamento
    logger.info("\n5️⃣ Aguardando processamento (verificando a cada 1s)...")
    tempo_inicio = time.time()
    timeout = 60
    last_size = get_queue_size()
    
    while time.time() - tempo_inicio < timeout:
        fila_size = get_queue_size()
        workers = get_worker_count()
        
        # Mostrar apenas se mudou
        if fila_size != last_size or workers != 3:
            logger.info(f"   ⏳ Fila: {fila_size} tarefas, Workers ativas: {workers}")
            last_size = fila_size
        
        if fila_size == 0:
            logger.info("   ✅ Fila vazia!")
            # Aguardar mais um pouco para garantir que as threads terminaram
            time.sleep(5)
            break
        
        time.sleep(1)
    
    if time.time() - tempo_inicio >= timeout:
        logger.error(f"   ⏱️ TIMEOUT! Fila ainda tem {get_queue_size()} tarefas após {timeout}s")
    
    # 6. Verificar status final
    logger.info("\n6️⃣ Status final dos produtos:")
    for p in ProdutoAutomatico.objects.filter(id__in=[p.id for p in produtos_teste]):
        logger.info(f"   Produto {p.id}: status={p.get_status_extracao_display()}, titulo={p.titulo or 'VAZIO'}")
    
    # 7. Verificar sucesso
    logger.info("\n7️⃣ RESULTADO:")
    sucesso_count = ProdutoAutomatico.objects.filter(
        id__in=[p.id for p in produtos_teste],
        status_extracao=StatusExtracao.SUCESSO
    ).count()
    
    if sucesso_count == len(produtos_teste):
        logger.info(f"   ✅ SUCESSO! Todos os {sucesso_count} produtos foram processados!")
    else:
        logger.error(f"   ❌ FALHA! Apenas {sucesso_count}/{len(produtos_teste)} foram processados")
        logger.error("   Possíveis causas:")
        logger.error("   - Workers não estão rodando (daemon threads morreram)")
        logger.error("   - Há erro no processamento da tarefa")
        logger.error("   - Timeout muito curto")
    
    logger.info("\n" + "="*60)


if __name__ == '__main__':
    main()
