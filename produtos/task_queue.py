"""
Fila de tarefas assíncrona para processamento de produtos.
Evita bloqueios no Django admin quando múltiplas plataformas são selecionadas.

CORREÇÃO: Processamento paralelo com múltiplos workers para evitar travamento
em ações do admin que processam múltiplos produtos simultâneos.
"""

import threading
import queue
import time
import logging
from typing import Callable, List, Dict, Any
from django.contrib import messages
from django.http import HttpRequest

logger = logging.getLogger(__name__)

# Configuração de workers paralelos
NUM_WORKERS = 3  # Máx 3 requisições de scraping em paralelo (controlado também no scraper)
_task_queue = queue.Queue()
_worker_threads = []
_workers_running = False  # Inicializar como False
_lock = threading.Lock()



def _worker(worker_id: int):
    """Worker thread que processa itens da fila de forma independente."""
    global _workers_running
    logger.info(f"👷 Worker #{worker_id} iniciado")
    
    while _workers_running:
        try:
            # Esperar por uma tarefa com timeout (evita CPU spinning)
            task_data = _task_queue.get(timeout=2)
            
            if task_data is None:  # Sinal para parar
                logger.info(f"👷 Worker #{worker_id} parado")
                break
            
            task_func = task_data['func']
            task_args = task_data.get('args', ())
            task_kwargs = task_data.get('kwargs', {})
            
            try:
                logger.debug(f"👷 Worker #{worker_id} processando: {task_func.__name__}")
                # Execute task - rate limiting é feito dentro do scraper agora
                task_func(*task_args, **task_kwargs)
            except Exception as e:
                logger.error(f"👷 Worker #{worker_id} erro: {e}", exc_info=True)
            finally:
                _task_queue.task_done()
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"👷 Worker #{worker_id} erro crítico: {e}", exc_info=True)


def _ensure_workers():
    """Garante que as worker threads estão rodando."""
    global _worker_threads, _workers_running
    
    with _lock:
        # Verificar se há workers mortos e remover
        _worker_threads = [w for w in _worker_threads if w.is_alive()]
        
        # Iniciar workers faltantes
        while len(_worker_threads) < NUM_WORKERS:
            _workers_running = True
            worker_id = len(_worker_threads) + 1
            thread = threading.Thread(
                target=_worker, 
                args=(worker_id,),
                daemon=True,
                name=f"TaskWorker-{worker_id}"
            )
            thread.start()
            _worker_threads.append(thread)
        
        if len(_worker_threads) > 0 and not _workers_running:
            _workers_running = True
            logger.info(f"✅ {NUM_WORKERS} worker threads ativas para processamento paralelo")



def queue_task(func: Callable, *args, **kwargs):
    """
    Adiciona uma tarefa à fila de processamento.
    Será executada por um dos workers paralelos em background.
    
    Args:
        func: Função a executar
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
    """
    _ensure_workers()
    
    task_data = {
        'func': func,
        'args': args,
        'kwargs': kwargs,
    }
    
    _task_queue.put(task_data)
    logger.debug(f"📋 Tarefa adicionada à fila (tamanho: {_task_queue.qsize()})")


def queue_batch_tasks(func: Callable, items: List[Any], rate_limit_ms: int = 100):
    """
    Adiciona múltiplas tarefas à fila para processamento paralelo.
    
    O rate limiting entre requisições é feito no scraper (não aqui).
    Múltiplos workers processam tarefas em paralelo, evitando gargalo.
    
    Args:
        func: Função a executar para cada item
        items: Lista de itens a processar
        rate_limit_ms: Delay mínimo entre enfileiramento (não execução)
    """
    _ensure_workers()
    
    for i, item in enumerate(items):
        task_data = {
            'func': func,
            'args': (item,),
            'kwargs': {},
        }
        _task_queue.put(task_data)
        
        # Pequeno delay apenas entre enfileiramento (não bloqueia execução)
        if i < len(items) - 1:
            time.sleep(rate_limit_ms / 1000.0)
    
    logger.info(f"📋 {len(items)} tarefa(s) enfileirada(s) para processamento paralelo "
                f"({NUM_WORKERS} workers ativos)")




def get_queue_size() -> int:
    """Retorna o número de tarefas aguardando na fila."""
    return _task_queue.qsize()


def get_worker_count() -> int:
    """Retorna o número de workers ativos."""
    return sum(1 for t in _worker_threads if t.is_alive())


def stop_workers():
    """Para todas as worker threads."""
    global _workers_running
    _workers_running = False
    
    # Enviar sinais de parada para cada worker
    for _ in _worker_threads:
        _task_queue.put(None)
    
    logger.info(f"⏹️ Solicitado parada de {len(_worker_threads)} workers")


def wait_all() -> bool:
    """
    Aguarda até que todas as tarefas sejam completadas.
    Retorna True se completou com sucesso, False se timeout.
    """
    try:
        _task_queue.join()
        logger.info("✅ Todas as tarefas foram completadas")
        return True
    except Exception as e:
        logger.error(f"Erro ao aguardar tarefas: {e}")
        return False

