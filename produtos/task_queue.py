"""
Fila de tarefas assíncrona para processamento de produtos.
Evita bloqueios no Django admin quando múltiplas plataformas são selecionadas.
"""

import threading
import queue
import time
import logging
from typing import Callable, List, Dict, Any
from django.contrib import messages
from django.http import HttpRequest

logger = logging.getLogger(__name__)

# Fila global para processamento assíncrono
_task_queue = queue.Queue()
_worker_thread = None
_worker_running = False
_lock = threading.Lock()


def _worker():
    """Worker thread que processa itens da fila."""
    global _worker_running
    _worker_running = True
    
    while _worker_running:
        try:
            # Esperar por uma tarefa com timeout
            task_data = _task_queue.get(timeout=1)
            
            if task_data is None:  # Sinal para parar
                break
            
            task_func = task_data['func']
            task_args = task_data.get('args', ())
            task_kwargs = task_data.get('kwargs', {})
            
            try:
                # Executar tarefa com rate limiting
                time.sleep(0.5)  # Delay entre requisições (500ms)
                task_func(*task_args, **task_kwargs)
            except Exception as e:
                logger.error(f"Erro ao executar tarefa: {e}", exc_info=True)
            finally:
                _task_queue.task_done()
                
        except queue.Empty:
            continue
        except Exception as e:
            logger.error(f"Erro no worker: {e}", exc_info=True)


def _ensure_worker():
    """Garante que a worker thread está rodando."""
    global _worker_thread, _worker_running
    
    with _lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_running = True
            _worker_thread = threading.Thread(target=_worker, daemon=True)
            _worker_thread.start()
            logger.info("✅ Worker thread iniciada")


def queue_task(func: Callable, *args, **kwargs):
    """
    Adiciona uma tarefa à fila de processamento.
    
    Args:
        func: Função a executar
        *args: Argumentos posicionais
        **kwargs: Argumentos nomeados
    """
    _ensure_worker()
    
    task_data = {
        'func': func,
        'args': args,
        'kwargs': kwargs,
    }
    
    _task_queue.put(task_data)
    logger.debug(f"📋 Tarefa adicionada à fila (tamanho atual: {_task_queue.qsize()})")


def queue_batch_tasks(func: Callable, items: List[Any], rate_limit_ms: int = 500):
    """
    Adiciona múltiplas tarefas à fila com rate limiting.
    
    Args:
        func: Função a executar para cada item
        items: Lista de itens a processar
        rate_limit_ms: Delay entre requisições em milissegundos
    """
    _ensure_worker()
    
    for item in items:
        task_data = {
            'func': func,
            'args': (item,),
            'kwargs': {},
        }
        _task_queue.put(task_data)
    
    logger.info(f"📋 {len(items)} tarefas adicionadas à fila (rate_limit={rate_limit_ms}ms)")


def get_queue_size() -> int:
    """Retorna o número de tarefas aguardando na fila."""
    return _task_queue.qsize()


def stop_worker():
    """Para a worker thread."""
    global _worker_running
    _worker_running = False
    _task_queue.put(None)  # Sinal para parar
    logger.info("⏹️ Worker thread parada")


def wait_all() -> bool:
    """
    Aguarda até que todas as tarefas sejam completadas.
    Retorna True se completou com sucesso, False se timeout.
    """
    try:
        _task_queue.join()
        return True
    except Exception as e:
        logger.error(f"Erro ao aguardar tarefas: {e}")
        return False
