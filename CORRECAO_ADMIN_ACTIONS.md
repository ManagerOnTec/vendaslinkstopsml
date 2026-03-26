# 🔧 CORREÇÕES - Admin Actions Extract/Re-Extract

## Problema Identificado

Quando você usa as **ações batch do Django admin** (Extrair/Re-extrair), os dados não são atualizados, mesmo que ao adicionar um produto individualmente funcione perfeitamente.

### Causas Raiz

#### 1. **Bug no Fallback asyncio.run()** ❌
**Arquivo:** `produtos/scraper.py` - função `extrair_dados_produto()`

**Problema:**
```python
# ANTES (QUEBRADO):
except RuntimeError as e:
    if 'asyncio.run() cannot be called from a running event loop' in str(e):
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(_detectar_plataforma_e_extrair, url)
            resultado = future.result(timeout=60)
            # ❌ Isto FALHA - asyncio.run() não pode ser chamado aqui!
            return resultado if resultado else asyncio.run(_extrair_dados_ml(url))
```

**Raiz:** Quando há um event loop rodando (raro mas possível em contextos ASGI), o código tenta usar ThreadPoolExecutor mas ainda chama `asyncio.run()` no final, que vai falhar.

**Correção:** ✅
- Detectar se há event loop rodando com `asyncio.get_running_loop()`
- Se houver, executar a detecção em uma **thread separada** que tem seu próprio event loop isolado
- Se não houver, usar `asyncio.run()` normalmente

```python
# DEPOIS (CORRETO):
def _executar_deteccao_no_loop():
    """Executa em um novo event loop isolado"""
    return _detectar_plataforma_e_extrair(url)

try:
    loop = asyncio.get_running_loop()
    # Event loop rodando - usar thread separada
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_executar_deteccao_no_loop)
        dados = future.result(timeout=90)
        if dados:
            return dados
        # Fallback em thread também
        future = executor.submit(_executar_ml_no_loop)
        return future.result(timeout=90)
except RuntimeError:
    # Nenhum event loop rodando - usar asyncio.run() direto
    dados = _detectar_plataforma_e_extrair(url)
```

---

#### 2. **Stale Data em Worker Threads** ❌
**Arquivo:** `produtos/scraper.py` - função `processar_produto_automatico()`

**Problema:**
Quando um worker thread processa um produto que foi passado da thread principal (admin), o objeto pode estar em estado desatualizado (*stale*). Isso causa problemas se:
- O produto foi modificado na thread principal depois de ser enfileirado
- A conexão de database foi reutilizada de outra thread

**Correção:** ✅
```python
# Recarregar produto do BD para garantir estado atual em worker threads
try:
    produto = ProdutoAutomatico.objects.get(pk=produto.pk)
except ProdutoAutomatico.DoesNotExist:
    logger.error(f"❌ Produto não encontrado no BD: pk={produto.pk}")
    return False

# Fechar connection anterior se houver (thread safety)
from django.db import connection
connection.close()
```

---

#### 3. **Logging Insuficiente em Workers** ❌
**Arquivo:** `produtos/task_queue.py` - função `_worker()`

**Problema:**
Se um worker falhava silenciosamente, não havia logs detalhados mostrando o produto que foi processado ou o erro exato.

**Correção:** ✅
- Log de qual produto foi processado (produto_id)
- Log do resultado (sucesso/falha)
- Rastreamento completo da exception com `exc_info=True`
- Logs diferenciados para sucesso vs falha

```python
produto_id = None
try:
    if task_args and hasattr(task_args[0], 'id'):
        produto_id = task_args[0].id
        logger.info(f"👷 Worker #{worker_id} processando: {task_func.__name__}(produto_id={produto_id})")
    
    result = task_func(*task_args, **task_kwargs)
    
    if result:
        logger.info(f"✅ Worker #{worker_id} completou com SUCESSO (produto_id={produto_id})")
    else:
        logger.warning(f"⚠️ Worker #{worker_id} completou mas resultado=False (produto_id={produto_id})")
        
except Exception as e:
    logger.error(
        f"❌ Worker #{worker_id} ERRO: {type(e).__name__}: {str(e)[:150]}", 
        exc_info=True
    )
    if produto_id:
        logger.error(f"   Produto ID: {produto_id}")
```

---

## Resumo das Mudanças

| Arquivo | Função | Problema | Solução |
|---------|--------|----------|---------|
| `scraper.py` | `extrair_dados_produto()` | Fallback asyncio quebrado | Event loop isolado em thread |
| `scraper.py` | `processar_produto_automatico()` | Stale data em threads | Recarregar do BD + fechar connection |
| `task_queue.py` | `_worker()` | Logging faltando | Logs detalhados de sucesso/erro |

---

## Como Testar

### Opção 1: Teste Diagnóstico Automático (RECOMENDADO)
```bash
python manage.py shell
exec(open('test_admin_actions_v2.py').read())
```

Este script vai:
1. ✅ Testar adição síncrona (como save_model)
2. ✅ Testar batch extract (como ação admin)
3. ✅ Testar batch re-extract (como ação admin)
4. 📊 Exibir resultado detalhado

### Opção 2: Teste Manual no Django Admin
1. Acesse `/admin/produtos/produtoautomativoproxy/`
2. Selecione 1-2 produtos
3. Use "Extrair/Atualizar dados" ou "Re-extrair dados"
4. **Verifique os logs** (logs de DEBUG com todos os detalhes)
5. Aguarde ~30 segundos e recarregue a página para ver se dados foram atualizados

### Observar Logs
Os logs agora mostram claramente:
- Qual worker processou qual produto
- Se completou com sucesso ou erro
- Exatamente qual erro aconteceu
- ID do produto sendo processado

```
[Worker-1] INFO Processando: processar_produto_automatico(produto_id=123)
[Worker-1] INFO ✅ Completou com SUCESSO (produto_id=123)
```

---

## Próximos Passos

1. **Fazer deploy** das mudanças em produção
2. **Rodar test_admin_actions_v2.py** para validar
3. **Testar no admin** com alguns produtos
4. **Monitorar logs** durante re-extrações em batch
5. Se houver 503 errors continuando, investigar a raiz (pode ser separada - health checks)

---

## Notas Importantes

### Sobre os erros 503 nos logs
Os erros 503 que você está vendo (GoogleStackdriverMonitoring-UptimeChecks) são **relacionados mas separados** deste problema do admin extract:
- 🔴 **503**: App retornando erro de serviço
- 🟡 **Admin actions não atualizam**: App não conseguindo processar corretamente

A correção acima resolve o **problema de admin actions**. Os **503 errors** podem ser causados por:
- ALLOWED_HOSTS ainda não configurado com `backcountry.s5stratos.com`
- App ficando indisponível durante processamento intensivo (possível deadlock)
- Database connection issues

Se após essas correções você ainda vir 503 errors, abra um novo issue focado nisso.

---

## Validação Final

Após fazer deploy:
1. Ir ao Django admin
2. Selecionar um produto
3. Usar ação "Re-extrair dados"
4. **Esperado:** Título, preço, imagem são atualizados em tempo real
5. **Logs:** Mostram sucesso de extração com produto_id

✅ Se isso funcionar, o problema foi resolvido!
