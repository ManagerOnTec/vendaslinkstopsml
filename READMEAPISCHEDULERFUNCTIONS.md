# 📚 Guia de Implementação: Cloud Functions + Scheduler

**Data**: Março 2026  
**Projeto**: Vendas Links Tops ML  
**Objetivo**: Atualização automática de produtos com baixo custo  
**Custo Estimado**: $0-6/mês

---

## 🏗️ Arquitetura da Solução

```
Cloud Scheduler (agendador - cron)
    ↓ (POST a cada 6h)
Cloud Functions (Python - orquestrador)
    ↓ (lê Secret Manager)
Cloud Run (Django App)
    ↓ (POST com Bearer token)
Endpoint: /api/scheduler/atualizar-produtos/
    ↓ (valida SECRET)
Management Command: atualizar_produtos_ml
    ↓
Database atualizado
```

---

## 📋 PASSO 1: Gerar Token Seguro

```bash
# No terminal local ou Cloud Shell
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Saída esperada: algo como
# aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5aB6cD7eF8gH9
```

**Salve este token em local seguro** - será usada em vários passos.

---

## 🔐 PASSO 2: Criar Secret no GCP Secret Manager

### Via Cloud Console:
1. Acesse **GCP Console → Security → Secret Manager**
2. Clique em **Create Secret**
3. **Name**: `SECRETKEYAPIAGENDAMENTO`
4. **Secret value**: Cole o token gerado no Passo 1
5. **Replication policy**: Automatic
6. Clique **Create Secret**

### Via gcloud CLI:
```bash
# Substitua SEU_TOKEN pelo valor gerado
echo "SEU_TOKEN" | gcloud secrets create SECRETKEYAPIAGENDAMENTO \
  --replication-policy="automatic" \
  --data-file=-

# Verificar
gcloud secrets list
gcloud secrets versions access latest --secret="SECRETKEYAPIAGENDAMENTO"
```

---

## 📝 PASSO 3: Atualizar Django Settings

**Arquivo**: `vendaslinkstopsml/settings.py`

Adicione ao final:

```python
# ===== SCHEDULER CONFIGURATION =====
SCHEDULER_SECRET_TOKEN = os.getenv('SECRETKEYAPIAGENDAMENTO', 'dev-secret-key')
```

---

## 🌐 PASSO 4: Criar Endpoint no Django

**Arquivo**: `produtos/views.py`

Adicione as imports no topo:
```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.conf import settings
import logging

logger = logging.getLogger(__name__)
```

Adicione a view ao final:
```python
@csrf_exempt
@require_http_methods(["POST"])
def trigger_product_update(request):
    """
    Endpoint disparado por Cloud Scheduler via Cloud Functions
    
    Requisitos:
    - POST request
    - Header: Authorization: Bearer {SECRETKEYAPIAGENDAMENTO}
    
    Retorna:
    - 200: {"status": "success", "message": "..."}
    - 401: Unauthorized
    - 500: Error details
    """
    # Validar Bearer token
    auth_header = request.headers.get('Authorization', '')
    expected_token = f'Bearer {settings.SCHEDULER_SECRET_TOKEN}'
    
    if auth_header != expected_token:
        logger.warning(f"❌ Unauthorized update attempt. Auth: {auth_header[:20]}...")
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    
    try:
        logger.info("🚀 Iniciando atualização automática de produtos ML")
        call_command('atualizar_produtos_ml')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Atualização de produtos concluída com sucesso'
        })
    
    except Exception as e:
        logger.error(f"❌ Erro ao atualizar produtos: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Erro: {str(e)}'
        }, status=500)
```

---

## 🔗 PASSO 5: Adicionar URL

**Arquivo**: `produtos/urls.py`

Adicione à lista `urlpatterns`:
```python
path('api/scheduler/atualizar-produtos/', views.trigger_product_update, name='scheduler_update'),
```

Resultado esperado:
```python
urlpatterns = [
    path('', ProdutosCombinedListView.as_view(), name='lista'),
    path('categoria/<slug:slug>/', CategoriaListView.as_view(), name='categoria'),
    path('api/scheduler/atualizar-produtos/', views.trigger_product_update, name='scheduler_update'),
    path('api/atualizar-produtos/', AtualizarProdutosAPIView.as_view(), name='api_atualizar'),
]
```

---

## 🎯 PASSO 6: Deploy no Cloud Run

Execute Deploy com a variável de ambiente:

```bash
# Login no GCP
gcloud auth login
gcloud config set project SEU_PROJETO_GCP

# Deploy do app
gcloud run deploy vendaslinkstopsml \
  --source . \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets SECRETKEYAPIAGENDAMENTO=SECRETKEYAPIAGENDAMENTO:latest
```

**Copie a URL do Cloud Run gerada**, exemplo:
```
https://vendaslinkstopsml-xxxxx.run.app
```

**Teste o endpoint manualmente**:
```bash
# Obter token do Secret Manager
TOKEN=$(gcloud secrets versions access latest --secret="SECRETKEYAPIAGENDAMENTO")

# Fazer requisição
curl -X POST https://vendaslinkstopsml-xxxxx.run.app/api/scheduler/atualizar-produtos/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Resposta esperada:
# {"status": "success", "message": "Atualização de produtos concluída com sucesso"}
```

---

## ⚡ PASSO 7: Criar Cloud Function

### Via Cloud Console:

1. Acesse **Cloud Functions**
2. Clique em **Create Function**
3. Configure:
   - **Name**: `atualizar-produtos-ml`
   - **Environment**: Python 3.11
   - **Trigger type**: HTTP
   - **Authentication**: Require authentication
   - **Runtime service account**: Compute Engine sa
4. Cole o código abaixo nos editores
5. Clique **Deploy**

### `main.py`:

```python
import functions_framework
import requests
import os
from google.cloud import secretmanager
import json

@functions_framework.http
def trigger_update(request):
    """
    Cloud Function que recupera Secret e dispara update no Cloud Run
    
    Espera variáveis de ambiente:
    - GCP_PROJECT: ID do projeto GCP
    - CLOUD_RUN_URL: URL do app no Cloud Run
    """
    try:
        # 1. Recuperar secret do Secret Manager
        secret_client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT')
        secret_name = f"projects/{project_id}/secrets/SECRETKEYAPIAGENDAMENTO/versions/latest"
        secret_response = secret_client.access_secret_version(request={"name": secret_name})
        secret_token = secret_response.payload.data.decode('UTF-8')
        
        # 2. URL do endpoint no Cloud Run
        cloud_run_url = os.environ.get('CLOUD_RUN_URL')
        if not cloud_run_url:
            return json.dumps({"status": "error", "message": "CLOUD_RUN_URL not configured"}), 500
        
        endpoint = f"{cloud_run_url}/api/scheduler/atualizar-produtos/"
        
        # 3. Fazer requisição com token
        headers = {
            'Authorization': f'Bearer {secret_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(endpoint, headers=headers, timeout=540)  # 9 min timeout
        
        return json.dumps({
            "status": "success",
            "message": f"Update triggered: HTTP {response.status_code}",
            "response": response.json()
        }), 200
    
    except Exception as e:
        return json.dumps({
            "status": "error",
            "message": str(e)
        }), 500
```

### `requirements.txt`:

```
functions-framework==3.5.0
requests==2.31.0
google-cloud-secret-manager==2.16.4
```

### Configurar Variáveis de Ambiente na Cloud Function:

Após criar a função, edite os **Runtime settings** e adicione:

```
Variáveis de ambiente:
GCP_PROJECT = seu-projeto-gcp
CLOUD_RUN_URL = https://vendaslinkstopsml-xxxxx.run.app
```

**Teste a Cloud Function**:
1. Acesse a função no Console
2. Clique em **Testing**
3. Clique **Run** 
4. Verifique os logs - deve retornar status 200 com sucesso

---

## 🕐 PASSO 8: Criar Cloud Scheduler Job

### Via Cloud Console:

1. Acesse **Cloud Scheduler**
2. Clique em **Create Job**
3. Configure:
   - **Name**: `atualizar-produtos-ml`
   - **Frequency**: `0 */6 * * *` (a cada 6 horas)
   - **Timezone**: `America/Sao_Paulo`
   - **Execution timezone**: UTC

4. Clique **Continue**
5. Configure:
   - **Execution type**: HTTP
   - **URL**: `https://us-central1-SEU_PROJETO.cloudfunctions.net/atualizar-produtos-ml`
   - **HTTP method**: POST
   - **Auth header**: Add OIDC token
   - **Service account**: Selecione `Compute Engine default service account`

6. Clique **Create**

### Via gcloud CLI:

```bash
gcloud scheduler jobs create http atualizar-produtos-ml \
  --location us-central1 \
  --schedule "0 */6 * * *" \
  --timezone "America/Sao_Paulo" \
  --http-method POST \
  --uri "https://us-central1-SEU_PROJETO.cloudfunctions.net/atualizar-produtos-ml" \
  --oidc-service-account-email=YOUR_SERVICE_ACCOUNT@appspot.gserviceaccount.com
```

### Testar Job Manualmente:

```bash
# Força execução imediata
gcloud scheduler jobs run atualizar-produtos-ml --location us-central1

# Ver logs
gcloud functions logs read atualizar-produtos-ml \
  --region us-central1 \
  --limit 50
```

---

## ✅ Checklist de Implementação

- [ ] Gerar token seguro com `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Criar Secret `SECRETKEYAPIAGENDAMENTO` no Secret Manager
- [ ] Adicionar `SCHEDULER_SECRET_TOKEN` em `settings.py`
- [ ] Criar função `trigger_product_update` em `produtos/views.py`
- [ ] Adicionar URL em `produtos/urls.py`
- [ ] Deploy no Cloud Run com `--set-secrets`
- [ ] Testar endpoint manualmente
- [ ] Criar Cloud Function com `main.py` e `requirements.txt`
- [ ] Configurar variáveis de ambiente na Cloud Function
- [ ] Testar Cloud Function
- [ ] Criar Cloud Scheduler Job
- [ ] Testar execução do job
- [ ] Verificar logs em Cloud Logging

---

## 📊 Resumo de Componentes

| Componente | Função | Custo |
|-----------|--------|-------|
| Cloud Scheduler | Agenda execução a cada 6h | ~$4/mês |
| Cloud Functions | Orquestra a atualização | ~$1-2/mês |
| Secret Manager | Armazena token seguro | Grátis |
| Cloud Run | App Django | Variável |
| **TOTAL** | | **$0-6/mês** |

---

## 🔍 Troubleshooting

### Cloud Scheduler não executa?
```bash
# Verificar status
gcloud scheduler jobs describe atualizar-produtos-ml --location us-central1

# Ver última execução
gcloud scheduler jobs run atualizar-produtos-ml --location us-central1 --run-now
```

### Cloud Function retorna erro?
```bash
# Ver logs detalhados
gcloud functions logs read atualizar-produtos-ml \
  --region us-central1 \
  --limit 100
```

### Endpoint retorna 401 Unauthorized?
- Verificar se Secret está criado: `gcloud secrets list`
- Verificar se Cloud Run tem a variável: `gcloud run services describe vendaslinkstopsml --region us-central1`
- Verificar token: `gcloud secrets versions access latest --secret="SECRETKEYAPIAGENDAMENTO"`

### Timeout na Cloud Function?
- Aumentar timeout da função para 540s (9 min)
- Verificar se Management Command está completando rápido
- Considerar async com Cloud Tasks

---

## 📚 Referências

- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Cloud Functions Documentation](https://cloud.google.com/functions/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Service Account](https://cloud.google.com/run/docs/configuring/service-accounts)

---

## 🚀 Próximas Melhorias (Futuro)

1. **Implementar retry automático** com exponential backoff
2. **Adicionar alertas** no Cloud Monitoring
3. **Usar Cloud Tasks** para maior reliability
4. **Implementar health checks** para verificar status da API
5. **Dashboard** com histórico de execuções
6. **Integrar com Slack** para notificações de sucesso/erro

---

**Documento criado em**: Março 23, 2026  
**Última atualização**: -  
**Status**: Pronto para implementação em produção
