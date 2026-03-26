#!/usr/bin/env python
"""
Script de diagnóstico com a função REAL processar_produto_automatico
"""
import os
import sys
import django
import logging
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from produtos.models import ProdutoAutomatico, OrigemProduto, StatusExtracao
from produtos.task_queue import queue_batch_tasks, get_queue_size
from produtos.scraper import processar_produto_automatico

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    logger.info("="*70)
    logger.info("🧪 TESTE COM FUNÇÃO REAL: processar_produto_automatico")
    logger.info("="*70)
    
    # Limpar produtos de teste anteriores
    logger.info("\n1️⃣ Limpando produtos anteriores...")
    deletados = ProdutoAutomatico.objects.filter(
        link_afiliado__startswith="https://www.mercadolivre.com.br/MLB3"
    ).delete()
    logger.info(f"   Deletados: {deletados[0]}")
    
    # Criar 1 produto real para teste
    logger.info("\n2️⃣ Criando 1 produto com link real do Mercado Livre...")
    
    # Link real de teste (produto real no ML - notebook)
    link_real = "https://www.mercadolivre.com.br/MLB3061156823-notebook-gamer-144hz-8gb-512gb-ssd-processador-intel-core-i5-11-ger-nvidia-geforce-gtx-1050-tela-156-polegadas-preto-acer-aspire-5/p/MLB3061156823"
    
    produto = ProdutoAutomatico.objects.create(
        link_afiliado=link_real,
        origem=OrigemProduto.AUTOMATICO,
        ativo=True,
        status_extracao=StatusExtracao.PENDENTE
    )
    logger.info(f"   ✓ Produto criado: ID={produto.id}, status={produto.get_status_extracao_display()}")
    
    # Enfileirar para processamento
    logger.info("\n3️⃣ Enfileirando para processamento...")
    queue_batch_tasks(processar_produto_automatico, [produto])
    
    # Aguardar processamento
    logger.info("\n4️⃣ Aguardando processamento (máx 30s)...")
    inicio = time.time()
    
    while time.time() - inicio < 30:
        produto.refresh_from_db()
        status = produto.get_status_extracao_display()
        logger.info(f"   Status: {status}, Fila: {get_queue_size()}")
        
        if status != "Processando":
            break
        time.sleep(2)
    
    # Resultado
    logger.info("\n5️⃣ RESULTADO FINAL:")
    produto.refresh_from_db()
    logger.info(f"   ID: {produto.id}")
    logger.info(f"   Status: {produto.get_status_extracao_display()}")
    logger.info(f"   Título: {produto.titulo or '(vazio)'}")
    logger.info(f"   Preço: {produto.preco or '(vazio)'}")
    logger.info(f"   Plataforma: {produto.get_plataforma_display() if produto.plataforma else '(não detectada)'}")
    logger.info(f"   Categoria: {produto.categoria or '(não extraída)'}")
    logger.info(f"   Erro: {produto.erro_extracao or '(nenhum)'}")
    
    if produto.status_extracao == StatusExtracao.SUCESSO:
        logger.info(f"\n   ✅ SUCESSO! Dados foram extraídos corretamente")
    elif produto.status_extracao == StatusExtracao.ERRO:
        logger.info(f"\n   ❌ ERRO ao extrair. Verifique: {produto.erro_extracao}")
    else:
        logger.info(f"\n   ⚠️ Status inesperado: {produto.status_extracao}")
    
    logger.info("="*70)


if __name__ == '__main__':
    main()
