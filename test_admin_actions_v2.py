"""
🔧 TESTE DIAGNÓSTICO COMPLETO - Admin Actions Extract/Re-extract
==============================================================

Simula o ciclo completo de:
1. ✅ Adicionar produto individual (save_model) - SÍNCRONO
2. ✅ Usar ação batch "extract" (queue_batch_tasks) - ASSÍNCRONO
3. ✅ Usar ação batch "re-extract" (queue_batch_tasks) - ASSÍNCRONO

Identifica:
- Se workers estão rodando
- Se tarefas estão sendo processadas
- Onde exatamente está falhando
- Problemas com database connections em threads
"""

import os
import sys
import django
import time
import logging

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.db import connection
from django.test.utils import override_settings
from produtos.models import ProdutoAutomatico, StatusExtracao, OrigemProduto
from produtos.scraper import processar_produto_automatico
from produtos.task_queue import (
    queue_batch_tasks, get_queue_size, get_worker_count,
    _worker_threads, _workers_running, _ensure_workers
)

# Setup logging com mais detalhes
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(threadName)-20s] %(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

# URLs de teste - produtos reais para validação
TEST_URLS = {
    'mercado_livre': 'https://www.mercadolivre.com.br/teclado-mecanico-rgb/p/MLB2745438934',
    'amazon': 'https://www.amazon.com.br/dp/B08RVPVVMC',
    'shopee': 'https://shopee.com.br/Teclado-Mec%C3%A2nico-p-123456789',
}

def limpar_produtos_teste():
    """Remove produtos de teste anteriores."""
    for url in TEST_URLS.values():
        ProdutoAutomatico.objects.filter(link_afiliado=url).delete()
    logger.info("✓ Produtos de teste anteriores removidos")

def test_sincronico(url: str, plataforma: str) -> bool:
    """
    TEST 1: Simula save_model do admin - processamento SÍNCRONO
    """
    logger.info("\n" + "="*70)
    logger.info(f"TEST 1: SÍNCRONO ({plataforma})")
    logger.info("="*70)
    
    produto = ProdutoAutomatico.objects.create(
        link_afiliado=url,
        origem=OrigemProduto.AUTOMATICO,
        status_extracao=StatusExtracao.PENDENTE
    )
    logger.info(f"✓ Produto criado: ID={produto.id}, Status={produto.status_extracao}")
    
    # Fechar connection antes (simular novo request)
    connection.close()
    
    logger.info("→ Processando SINCRONAMENTE (como save_model faz)...")
    start = time.time()
    
    try:
        resultado = processar_produto_automatico(produto)
        elapsed = time.time() - start
        
        # Recarregar
        produto.refresh_from_db()
        
        logger.info(f"✓ Processamento completou em {elapsed:.2f}s")
        logger.info(f"  Resultado: {resultado}")
        logger.info(f"  Status: {produto.status_extracao}")
        logger.info(f"  Título: {(produto.titulo or 'NÃO EXTRAÍDO')[:60]}")
        logger.info(f"  Preço: {(produto.preco or 'NÃO EXTRAÍDO')[:30]}")
        logger.info(f"  Erro: {(produto.erro_extracao or 'Nenhum')[:80]}")
        
        if produto.status_extracao == StatusExtracao.SUCESSO and produto.titulo:
            logger.info("✅ TEST 1 PASSOU: Dados extraídos com sucesso")
            return True
        else:
            logger.error("❌ TEST 1 FALHOU: Dados não foram extraídos")
            return False
            
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ Erro após {elapsed:.2f}s: {type(e).__name__}: {e}", exc_info=True)
        return False


def test_batch_extract(url: str, plataforma: str) -> bool:
    """
    TEST 2: Simula extrair_dados_action - processamento em BATCH (async)
    """
    logger.info("\n" + "="*70)
    logger.info(f"TEST 2: BATCH - EXTRACT ({plataforma})")
    logger.info("="*70)
    
    # Criar novo produto
    produto = ProdutoAutomatico.objects.create(
        link_afiliado=url.replace('/p/', '/p-'),  # URL ligeiramente diferente para não conflitar
        origem=OrigemProduto.AUTOMATICO,
        status_extracao=StatusExtracao.PENDENTE
    )
    logger.info(f"✓ Produto criado: ID={produto.id}, Status={produto.status_extracao}")
    
    # Verificar workers
    _ensure_workers()
    worker_count = get_worker_count()
    logger.info(f"✓ Workers rodando: {worker_count}")
    
    if worker_count == 0:
        logger.error("❌ ERRO: Nenhum worker ativo!")
        return False
    
    # Enfileirar (como extrair_dados_action faz)
    logger.info(f"→ Enfileirando com {worker_count} workers...")
    queue_batch_tasks(processar_produto_automatico, [produto])
    logger.info(f"✓ Tarefa enfileirada. Fila: {get_queue_size()} itens")
    
    # Aguardar processamento (máx 45 segundos)
    logger.info("→ Aguardando processamento...")
    
    sucesso = False
    for i in range(45):
        time.sleep(1)
        
        # Recarregar
        produto.refresh_from_db()
        queue_size = get_queue_size()
        workers = get_worker_count()
        
        status_emoji = {
            StatusExtracao.PENDENTE: '⏳',
            StatusExtracao.PROCESSANDO: '🔄',
            StatusExtracao.SUCESSO: '✅',
            StatusExtracao.ERRO: '❌',
        }.get(produto.status_extracao, '❓')
        
        print(f"   [{i+1:2d}s] {status_emoji} Status: {produto.status_extracao:12s} | "
              f"Fila: {queue_size} | Workers: {workers} | "
              f"Título: {(produto.titulo or 'VAZIO')[:35]}")
        
        # Se completou, verificar sucesso
        if produto.status_extracao in [StatusExtracao.SUCESSO, StatusExtracao.ERRO]:
            if produto.status_extracao == StatusExtracao.SUCESSO and produto.titulo:
                sucesso = True
            break
    
    # Resultado
    logger.info(f"\n✓ Resultado final:")
    logger.info(f"  Status: {produto.status_extracao}")
    logger.info(f"  Título: {(produto.titulo or 'NÃO EXTRAÍDO')[:60]}")
    logger.info(f"  Preço: {(produto.preco or 'NÃO EXTRAÍDO')[:30]}")
    logger.info(f"  Erro: {(produto.erro_extracao or 'Nenhum')[:80]}")
    
    if sucesso:
        logger.info("✅ TEST 2 PASSOU: Batch extract funcionando")
    else:
        logger.error("❌ TEST 2 FALHOU: Batch não extraiu dados")
    
    return sucesso


def test_batch_reextract(produto_id: int, plataforma: str) -> bool:
    """
    TEST 3: Simula reextrair_dados_action - forçar re-extração
    """
    logger.info("\n" + "="*70)
    logger.info(f"TEST 3: BATCH - RE-EXTRACT ({plataforma})")
    logger.info("="*70)
    
    try:
        produto = ProdutoAutomatico.objects.get(pk=produto_id)
    except:
        logger.error(f"❌ Produto {produto_id} não encontrado")
        return False
    
    # Resetar status (como reextrair_dados_action faz)
    produto.status_extracao = StatusExtracao.PROCESSANDO
    produto.save()
    logger.info(f"✓ Produto resetado: ID={produto.id}, Status={StatusExtracao.PROCESSANDO}")
    
    # Enfileirar novamente
    logger.info("→ Enfileirando para re-extração...")
    queue_batch_tasks(processar_produto_automatico, [produto])
    logger.info(f"✓ Fila: {get_queue_size()}")
    
    # Aguardar
    logger.info("→ Aguardando re-processamento...")
    for i in range(30):
        time.sleep(1)
        produto.refresh_from_db()
        queue_size = get_queue_size()
        
        status_emoji = {
            StatusExtracao.PENDENTE: '⏳',
            StatusExtracao.PROCESSANDO: '🔄',
            StatusExtracao.SUCESSO: '✅',
            StatusExtracao.ERRO: '❌',
        }.get(produto.status_extracao, '❓')
        
        print(f"   [{i+1:2d}s] {status_emoji} {produto.status_extracao:12s} | Fila: {queue_size}")
        
        if produto.status_extracao in [StatusExtracao.SUCESSO, StatusExtracao.ERRO]:
            break
    
    if produto.status_extracao == StatusExtracao.SUCESSO:
        logger.info("✅ TEST 3 PASSOU: Re-extract funcionando")
        return True
    else:
        logger.error("❌ TEST 3 FALHOU: Re-extract não completou")
        logger.error(f"   Status: {produto.status_extracao}, Erro: {produto.erro_extracao[:80]}")
        return False


def main():
    """Executa todos os testes."""
    logger.info("\n")
    logger.info("╔" + "="*68 + "╗")
    logger.info("║" + " TESTE DIAGNÓSTICO COMPLETO - ADMIN ACTIONS ".center(68) + "║")
    logger.info("╚" + "="*68 + "╝")
    
    limpar_produtos_teste()
    
    resultados = {
        'sincrono': [],
        'batch_extract': [],
        'batch_reextract': [],
    }
    
    # Testar com Mercado Livre (plataforma mais confiável)
    url_ml = TEST_URLS['mercado_livre']
    
    # TEST 1: Síncrono
    resultado1 = test_sincronico(url_ml, 'Mercado Livre')
    resultados['sincrono'].append(resultado1)
    
    time.sleep(2)
    
    # TEST 2: Batch Extract
    resultado2 = test_batch_extract(url_ml, 'Mercado Livre')
    resultados['batch_extract'].append(resultado2)
    
    time.sleep(2)
    
    # TEST 3: Batch Re-extract (precisa de um produto do TEST 2)
    try:
        produto_teste = ProdutoAutomatico.objects.filter(
            link_afiliado__contains='p-',
            origem=OrigemProduto.AUTOMATICO
        ).first()
        if produto_teste:
            resultado3 = test_batch_reextract(produto_teste.id, 'Mercado Livre')
            resultados['batch_reextract'].append(resultado3)
    except Exception as e:
        logger.error(f"Erro em TEST 3: {e}")
        resultado3 = False
        resultados['batch_reextract'].append(resultado3)
    
    # RESUMO FINAL
    logger.info("\n\n" + "="*70)
    logger.info("RESUMO FINAL")
    logger.info("="*70)
    
    test1_ok = all(resultados['sincrono'])
    test2_ok = all(resultados['batch_extract'])
    test3_ok = all(resultados['batch_reextract']) if resultados['batch_reextract'] else False
    
    logger.info(f"\n1️⃣  SÍNCRONO (save_model):          {'✅ PASSOU' if test1_ok else '❌ FALHOU'}")
    logger.info(f"2️⃣  BATCH EXTRACT (async):         {'✅ PASSOU' if test2_ok else '❌ FALHOU'}")
    logger.info(f"3️⃣  BATCH RE-EXTRACT (async):      {'✅ PASSOU' if test3_ok else '❌ FALHOU'}")
    
    logger.info(f"\n{'✅ TODOS OS TESTES PASSARAM!' if test1_ok and test2_ok and test3_ok else '❌ ALGUNS TESTES FALHARAM'}\n")
    
    if not test2_ok:
        logger.error("\n⚠️  PROBLEMA IDENTIFICADO: Ações admin (batch/async) não funcionando!")
        logger.error("   Próximas ações:")
        logger.error("   1. Verificar logs detalhados acima")
        logger.error("   2. Confirmar que workers estão rodando")
        logger.error("   3. Verificar erros de asyncio/database connection")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nTeste interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\nErro crítico: {e}", exc_info=True)
        sys.exit(1)
