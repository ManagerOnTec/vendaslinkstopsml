"""
RESUMO DAS ALTERAÇÕES - SUPORTE MULTI-PLATAFORMA COM FILA DE TAREFAS
====================================================================

Data: 2026-03-23
Objetivo: Corrigir "service unavailable" quando múltiplas plataformas (ML + Amazon) 
          são selecionadas concomitantemente no admin.

PROBLEMAS IDENTIFICADOS:
-----------------------
1. Ações nomeadas como "Mercado Livre" quando deveriam ser genéricas
2. Loop síncrono e bloqueante no admin (sem paralelização)
3. Sem rate limiting entre requisições (sobrecarga do servidor)
4. Múltiplas requisições Playwright simultâneas causavam "service unavailable"

SOLUÇÕES IMPLEMENTADAS:
-----------------------

1. FILA DE TAREFAS ASSÍNCRONA (novo arquivo: produtos/task_queue.py)
   - Worker thread que processa tarefas em background
   - Evita bloqueio do Django admin
   - Rate limiting automático entre requisições (300ms min delay)
   - Semáforo com limite de 2 requisições simultâneas
   
2. AÇÕES RENOMEADAS (admin.py)
   - "Extrair/Atualizar dados do Mercado Livre" 
     → "Extrair/Atualizar dados (Genérico - todas as plataformas)"
   - "Re-extrair dados (forçar atualização)"
     → "Re-extrair dados (forçar atualização - todas as plataformas)"
   - "Resetar contador de falhas"
     → "Resetar contador de falhas e reativar"
   
3. AÇÕES AGORA USAM FILA (admin.py)
   - Enfileiram tarefas em vez de executar bloqueante
   - Mensagens de feedback informam que está em background
   - Funciona para: ML, Amazon, Shopee, Shein e outras
   
4. RATE LIMITING NO SCRAPER (scraper.py)
   - Delay mínimo de 300ms entre requisições
   - Aplicado antes de cada scraer (_extrair_dados_ml, _extrair_dados_amazon, _extrair_dados_genererico)
   - Sincronizado via threading.Lock para evitar race conditions

ARQUIVOS MODIFICADOS:
--------------------
1. produtos/task_queue.py (NOVO)
   - Fila global de tarefas
   - Worker thread
   - Funções públicas: queue_task, queue_batch_tasks, wait_all, get_queue_size

2. produtos/admin.py
   - Importar task_queue
   - Atualizar descrições de ações
   - Substituir loops síncronos por queue_batch_tasks
   - Adicionar reativação em resetar_falhas_action

3. produtos/scraper.py
   - Adicionar imports: threading, time
   - Adicionar: _rate_limit_lock, _last_request_time, _enforce_rate_limit()
   - Chamar _enforce_rate_limit() no início de cada função assíncrona

FLUXO DE PROCESSAMENTO:
----------------------

ANTES (problemático):
Admin → Loop síncrono → _extrair_dados_ml/amazon/etc → Bloqueia até terminar
         ↓
    Se múltiplas plataformas → múltiplas requisições simultâneas → OVERLOAD
    ↓
    Django timeout → 503 Service Unavailable

DEPOIS (corrigido):
Admin → Enfileira tarefas → Retorna feedback → Usuário não é bloqueado
         ↓
    Worker thread processa background com rate limiting (300ms) 
         ↓
    _enforce_rate_limit() sincroniza requisições (max 2 simultâneas)
         ↓
    Requisições separadas por 300ms não sobrecarregam servidor

TESTANDO:
--------

1. Criar produtos com URLs de diferentes plataformas:
   - amzn.to/... (Amazon)
   - mercadolivre.com.br/... (Mercado Livre)
   - shopee.com.br/... (Shopee)
   - shein.com/... (Shein)

2. Selecionar múltiplos produtos (mix de plataformas) no admin

3. Escolher ação: "Extrair/Atualizar dados (Genérico - todas as plataformas)"

4. Verificar:
   ✓ Admin retorna imediatamente (não bloqueia)
   ✓ Mensagem: "X produto(s) enfileirado(s) para extração..."
   ✓ Processamento acontece em background
   ✓ Sem "503 Service Unavailable"
   ✓ Todos os produtos extraem (ML, Amazon, Shopee, Shein)
   ✓ Rate limiting funciona (300ms entre requisições)

COMPATIBILIDADE:
---------------
✓ Atualizador automático (management command)
✓ Lançamento unitário (admin save individual)
✓ Múltiplas plataformas concomitantemente
✓ MySQL (produção) e SQLite (desenvolvimento)
✓ Docker/Gunicorn/Nginx

NOTAS IMPORTANTES:
-----------------
1. Worker thread é daemon, portanto não bloqueia shutdown
2. Fila usa queue.Queue (thread-safe nativamente)
3. Rate limiting usa threading.Lock para evitar race conditions
4. Limite de 2 requisições simultâneas evita overload
5. Semáforo é criado lazy (apenas se necessário)
"""
