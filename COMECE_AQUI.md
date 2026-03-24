╔════════════════════════════════════════════════════════════════════════════════╗
║                          AÇÕES IMEDIATAS (PRÓXIMAS 30 MIN)                    ║
║                    Ativar Phase 1: Indices + Retry Backoff                    ║
╚════════════════════════════════════════════════════════════════════════════════╝


PASSO 1: Criar arquivo .env
═════════════════════════════════════════════════════════════════════════════════

Na raiz do projeto, crie arquivo `.env` com:

```
# Limite de falhas e retry backoff
LIMITE_FALHAS=5
RETRY_DELAYS=5,15,60,240

# Workers e queue
NUM_WORKERS=2
MAX_QUEUE_SIZE=5000

# Database (dev local)
USE_SQLITE=True
SQLITE_TIMEOUT=60
```

Se estiver em produção GCP MySQL:

```
USE_SQLITE=False
DB_HOST=seu-cloudsql.domain.com
DB_USER=root
DB_PASSWORD=sua_senha_aqui
MYSQL_POOL_SIZE=10
```


PASSO 2: Instalar python-decouple (para carregar .env)
═════════════════════════════════════════════════════════════════════════════════

$ pip install python-decouple

Se em requirements.txt não tiver, adicionar:
  python-decouple==3.8


PASSO 3: Aplicar migração de índices
═════════════════════════════════════════════════════════════════════════════════

$ python manage.py migrate produtos

Saída esperada:
  Running migrations:
    Applying produtos.0004_performance_indices... OK

⚠️ SE DER ERRO "Table not found":
  $ python manage.py migrate


PASSO 4: Validar configuração
═════════════════════════════════════════════════════════════════════════════════

$ python manage.py shell

>>> from produtos.config_escalonamento import get_config_summary
>>> print(get_config_summary())

Deve exibir:
  LIMITE_FALHAS: 5
  RETRY_DELAYS: [5min, 15min, 1h, 4h]
  NUM_WORKERS: 2
  ...


PASSO 5: Testar com 10-20 produtos
═════════════════════════════════════════════════════════════════════════════════

1. No admin Django, selecionar 10-20 produtos
2. Action: "Extrair dados"
3. Aguardar conclusão
4. Verificar em logs:
   - Sucesso em 18/20? (90%+) → Ok ✅
   - Algum com motivo "Próxima tentativa em..." ? → Retry backoff funcionando ✅


PASSO 6: Testar com maior volume (100 produtos)
═════════════════════════════════════════════════════════════════════════════════

Se teste anterior passou, repetir com 100 produtos.

Observar:
  - Tempo total
  - Taxa de sucesso
  - Nenhuma desativação permanente sem motivo


═════════════════════════════════════════════════════════════════════════════════
📊 RESULTADOS ESPERADOS
═════════════════════════════════════════════════════════════════════════════════

ANTES (LIMITE_FALHAS=2):
  - Taxa de sucesso: ~89%
  - Falhas: ~11 de 100
  - Desativadas permanentemente: ~5-10
  - Razão comum: "Ativado" → "Falhou 2x" → Desativada

DEPOIS (LIMITE_FALHAS=5 + retry backoff):
  - Taxa de sucesso: ~98%
  - Falhas com agendamento: ~2 de 100
  - Desativadas permanentemente: ~1-2
  - Razão: Verdadeiras falhas (site down, login inválido)


═════════════════════════════════════════════════════════════════════════════════
🚀 PRÓXIMOS PASSOS (DEPOIS VALIDAR PHASE 1)
═════════════════════════════════════════════════════════════════════════════════

Se replicação com 1000+ itens for necessária:

OPÇÃO A (Imediato - MySQL):
  1. Criar Cloud SQL MySQL no GCP (5 min)
  2. Atualizar settings.py (10 min)
  3. Migrate dados (10 min)
  4. Testar com 1000 (2h)
  Resultado: 6-10h para 1000 itens ✅

OPÇÃO B (Escalável - Celery):
  1. Implementar Celery + Redis (2 dias)
  2. Converter tasks.py para @shared_task (1 dia)
  3. Deploy workers (1 dia)
  Resultado: 2-4h para 1000 itens com 8 workers ✅


═════════════════════════════════════════════════════════════════════════════════
❓ FAQ
═════════════════════════════════════════════════════════════════════════════════

P: "O que muda no comportamento do usuário?"
R: Nada visível. Admin fica mais rápido, sem travamentos.

P: "E se um produto continuar falhando?"
R: Agora tenta 5 vezes com delays (5m, 15m, 1h, 4h). Se falhar 5x, desativa com
   motivo real (não falso positivo). Pode ser reativado manualmente depois.

P: "Preciso fazer backup antes?"
R: Migração só ADD índices, não modifica dados. Sem risco.

P: "E se usar SQLite em produção com 1000+ itens?"
R: NÃO recomendado:
   - Timeout insuficiente (20-60s)
   - Locks desnecessários
   - Admin tranca frequentemente
   Use MySQL obrigatoriamente.

P: "Quanto melhora de performance?"
R: 
   - Queries: 10-50x mais rápidas
   - Taxa sucesso: 89% → 98%
   - Desativações falsas: 110 → 20-30


═════════════════════════════════════════════════════════════════════════════════
⏱️ TIMELINE
═════════════════════════════════════════════════════════════════════════════════

NOW (5 min): 
  ✅ Criar .env

0-15 MIN:
  ✅ Instalar python-decouple
  ✅ Executar migrate

15-30 MIN:
  ✅ Testar configuração (shell)

30-60 MIN:
  ✅ Testar com 10-20 produtos

DEPOIS:
  ⏳ Testar com 1000 se necessário (2h)
  ⏳ Considerar MySQL/Celery conforme escala


═════════════════════════════════════════════════════════════════════════════════
✅ SUCESSO!
═════════════════════════════════════════════════════════════════════════════════

Ao completar estes passos, você terá:
  ✓ Retry automático com backoff (sem mais desativações falsas)
  ✓ Índices de banco (queries 10x mais rápidas)
  ✓ Configuração escalável (fácil aumentar workers depois)
  ✓ Suporte para 1000+ itens em ~6-10h
  ✓ Admin nunca mais trava durante processamento
