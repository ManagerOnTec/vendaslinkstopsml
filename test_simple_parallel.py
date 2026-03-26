#!/usr/bin/env python
"""Teste rápido de paralelismo da fila"""

import os
import sys
import time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from produtos.task_queue import queue_task, get_queue_size, get_worker_count, wait_all

processed = []

def dummy_task(task_id):
    """Tarefa que simula processamento."""
    processed.append(task_id)
    print(f"   Task {task_id} completa (processados: {len(processed)})")
    time.sleep(0.05)

print("\nTestando paralelismo com múltiplos workers...")
print(f"Workers ativos: {get_worker_count()}\n")

print("Enfileirando 6 tarefas...")
for i in range(6):
    queue_task(dummy_task, i)

print(f"Fila tamanho: {get_queue_size()}, Workers: {get_worker_count()}\n")

start = time.time()
wait_all()
elapsed = time.time() - start

print(f"\n✅ Processamento completo")
print(f"Tempo: {elapsed:.2f}s (esperado: ~0.1s-0.3s com 3 workers paralelos)")
print(f"Tarefas processadas: {len(processed)}")
print(f"Paralelismo: {'✅ FUNCIONANDO' if elapsed < 0.5 else '⚠️ SEQUENCIAL'}")

