# Configuração de ALLOWED_HOSTS no GCP Cloud Run

## Problema
```
django.core.exceptions.DisallowedHost: Invalid HTTP_HOST header: 'backcountry.s5stratos.com'. 
You may need to add 'backcountry.s5stratos.com' to ALLOWED_HOSTS.
```

## Root Cause
A função `request.get_host()` [django/http/request.py:202] valida o header HTTP_HOST contra ALLOWED_HOSTS. Se a variável de ambiente `ALLOWED_HOSTS` não estiver configurada no Cloud Run, o site rejeita requisições de qualquer domínio.

## Onde o erro é disparado
1. **Arquivo**: `django/http/request.py`, linha 202 na função `get_host()`
2. **Middleware**: `django/middleware/common.py`, linha 48 em `process_request()`
3. **Acionador**: Qualquer requisição HTTP onde o header `Host` não está em `ALLOWED_HOSTS`

## Solução - Configurar ALLOWED_HOSTS no Cloud Run

### Passo 1: Acessar Cloud Run Console
```
https://console.cloud.google.com/run
```

### Passo 2: Editar o serviço
1. Clique no serviço `sitevendaslinkstopsml`
2. Clique em **"Editar e redimensionar"**
3. Clique na aba **"Variáveis e segredos"**

### Passo 3: Adicionar a variável de ambiente
Adicione ou atualize:
```
Nome: ALLOWED_HOSTS
Valor: backcountry.s5stratos.com,seu-outro-dominio.com

Exemplo com vários domínios:
ALLOWED_HOSTS=backcountry.s5stratos.com,example.com,www.example.com,localhost,127.0.0.1
```

### Passo 4: Deploy
1. Clique em **"Criar"** ou **"Atualizar"**
2. Aguarde o redeploy automático

## Alternativa: Via gcloud CLI

```bash
# Atualizar variável de ambiente
gcloud run services update sitevendaslinkstopsml \
  --region us-central1 \
  --set-env-vars ALLOWED_HOSTS=backcountry.s5stratos.com,seu-outro-dominio.com
```

## Debugging

Os logs agora mostram informações úteis:

```
⚠️ ALLOWED_HOSTS está vazio em produção!
   Host da requisição: backcountry.s5stratos.com
   Configure a variável de ambiente: ALLOWED_HOSTS=backcountry.s5stratos.com
```

## Melhorias implementadas

### 1. Middleware de Validação de Host
- Arquivo: `produtos/middleware.py` - `HostValidationMiddleware`
- Registra qual host foi rejeitado
- Sugere qual valor adicionar a ALLOWED_HOSTS

### 2. Configuração mais robusta
- Arquivo: `vendaslinkstopsml/settings.py`
- Em DEBUG: aceita `['localhost', '127.0.0.1', '0.0.0.0', '*']`
- Em PRODUÇÃO: requer configuração explícita
- Aviso no boot se não estiver configurado

## Checklist
- [ ] Variável `ALLOWED_HOSTS` configurada no Cloud Run
- [ ] Todos os domínios relacionados adicionados (com e sem www)
- [ ] Deploy realizado
- [ ] Testar acesso: `https://backcountry.s5stratos.com`
- [ ] Verificar logs em Cloud Logging

## Domínios comuns a adicionar
```
# Para site de vendas
backcountry.s5stratos.com
www.backcountry.s5stratos.com

# Para desenvolvimento
localhost
127.0.0.1
0.0.0.0

# Para API/Webhooks (se aplicável)
api.backcountry.s5stratos.com
```

## Referências
- [Django ALLOWED_HOSTS](https://docs.djangoproject.com/en/5.0/ref/settings/#allowed-hosts)
- [Cloud Run Variables](https://cloud.google.com/run/docs/configuring/environment-variables)
- [Cloud Logging](https://cloud.google.com/logging)
