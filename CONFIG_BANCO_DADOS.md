╔════════════════════════════════════════════════════════════════════════════════╗
║           CONFIGURAÇÃO VIA DJANGO ADMIN (Sem .env, Sem Redeploy)              ║
║                         Otimizado para GCP Cloud Run                           ║
╚════════════════════════════════════════════════════════════════════════════════╝


📊 O NOVO SISTEMA
═══════════════════════════════════════════════════════════════════════════════

ANTES (Decouple + .env):
  ❌ Precisa de .env ou variáveis de ambiente do Cloud Run
  ❌ Mudança requer redeploy
  ❌ Difícil testar diferentes configs sem CI/CD

AGORA (Banco de Dados + Django Admin):
  ✅ Configuração armazenada no MySQL/PostgreSQL
  ✅ Editar via Django Admin (interface visual)
  ✅ Mudanças entram em efeito IMEDIATAMENTE (sem redeploy)
  ✅ Fallback para env vars se banco não estiver disponível
  ✅ Histórico de mudanças via "nota" field
  ✅ Ideal para GCP Cloud Run com múltiplas instâncias


🔄 FLUXO DE CARREGAMENTO
═══════════════════════════════════════════════════════════════════════════════

Quando o scraper precisa de uma config (ex: LIMITE_FALHAS):

  1. Tenta carregar do BANCO DE DADOS
     └─ Se existir: usa valor
     └─ Se não existir (migrations não rodaram ainda):

  2. Tenta VARIÁVEIS DE AMBIENTE
     └─ Se env var existir: usa valor
     └─ Se não existir:

  3. Usa DEFAULT hardcoded
     └─ Ex: LIMITE_FALHAS=5


✨ BENEFÍCIOS
═══════════════════════════════════════════════════════════════════════════════

Cenário 1: Produção GCP com taxa de falha ↑
  Antes: "Precisa mudar .env, fazer commit, deploy"  (30+ min)
  Agora: Admin → Aumentar LIMITE_FALHAS para 7 → Salvar           (2 min)

Cenário 2: Testes com diferentes configs
  Antes: Criar .env.test, .env.staging, .env.prod  (confusão)
  Agora: Única configuração no banco, editar conforme necessário

Cenário 3: Múltiplas instâncias no Cloud Run
  Antes: Todas precisavam da mesma .env
  Agora: Todas leem a mesma config do BD (centralizado, sem conflitos)


🚀 IMPLEMENTAÇÃO
═══════════════════════════════════════════════════════════════════════════════

PASSO 1: Executar Migrations
────────────────────────────

$ python manage.py migrate produtos

Saída esperada:
  Applying produtos.0005_escalonamentoconfig... OK


PASSO 2: Verificar que Config foi Criada
──────────────────────────────────────────

$ python manage.py shell
>>> from produtos.models import EscalonamentoConfig
>>> config = EscalonamentoConfig.obter_config()
>>> print(config.limite_falhas)
5

>>> # Ou ver o resumo
>>> from produtos.config_escalonamento import get_config_summary
>>> import json
>>> print(json.dumps(get_config_summary(), indent=2))


PASSO 3: Acessar Django Admin
──────────────────────────────

URL: https://seu-site.com/admin/

Loguinput com superuser
Ir para: Produtos → Configurações de Escalonamento

(Vai ter apenas 1 registro editável)


PASSO 4: Editar Configuração no Admin
──────────────────────────────────────

Cada campo tem:
  • Label legível
  • Help text explicativo
  • Valor padrão sensato
  • Campo "Notas" para documentar mudanças

Exemplo 1: Mudar LIMITE_FALHAS
  Atual: 5
  Problema: Muitos falsos positivos (sites lentos)
  Solução: Aumentar para 7
  Ação:
    1. Admin → Escalonamento
    2. Limite de Falhas Consecutivas: 5 → 7
    3. Notas: "Aumentado para 7 (23/03/2026) - muitos timeouts em shopee"
    4. Salvar
  Resultado: Próxima falha do scraper usa LIMITE_FALHAS=7

Exemplo 2: Aumentar Paralelismo
  Atual: NUM_WORKERS=2
  Problema: Processamento de 1000 itens levando 10h
  Solução: Aumentar workers
  Ação:
    1. Admin → Escalonamento
    2. Número de Workers: 2 → 4 (se tiver CPU/RAM availability)
    3. Notas: "Aumentado de 2→4 workers (23/03/2026) - teste escalabilidade 1000 itens"
    4. Salvar
  Resultado: Próxima execução usa 4 workers em paralelo


❗ NÃO ESQUECER: Variáveis de Ambiente Ainda Servem Como Fallback
════════════════════════════════════════════════════════════════════

Se você quer "forçar" um valor via env var (ignorando o banco):

  1. Django Admin sempre é consultado PRIMEIRO
  2. Se quiser ignorar admin, você PRECISA comentar DB lookup em config_escalonamento.py

Caso de uso: Staging quer uma config diferente de Produção

  OPÇÃO A (Recomenddo): Usar 2 bancos diferentes
    $ export DB_HOST=staging-mysql.cloudsql.internal  # Staging aponta a outro DB
    $ export DB_HOST=prod-mysql.cloudsql.internal     # Prod aponta a outro DB

  OPÇÃO B: Usar env vars como override (implementação customizada)
    Se necessário, editar _load_config_from_db_or_env() em config_escalonamento.py
    para verificar env var ANTES do banco


📝 GCP CLOUD RUN VENV
════════════════════════════════════════════════════════════════════

Se seus env vars do Cloud Run têm vários valores, a prioridade é:

  1. Django Admin (banco) ← Predomina
  2. Cloud Run env vars
  3. Default em config_escalonamento.py


Como configurar no GCP Console:

  Cloud Run → seu-service → Edit & Deploy
  
  Environment variables:
    ✅ DJANGO_SUPERUSER_PASSWORD=***
    ❌ LIMITE_FALHAS=5               (NÃO precisa, está no AdminBD)
    ❌ NUM_WORKERS=2                 (NÃO precisa, está no Admin BD)
    ✅ DATABASE_URL=...              (precisa)
    ✅ SECRET_KEY=...                (precisa)
    ✅ OPERATION_MODE=production     (opcional, control)


🔍 DEBUG: Como Ver de Onde Vem a Config
═════════════════════════════════════════

$ python manage.py shell
>>> from produtos.config_escalonamento import get_config_info
>>> print(get_config_info())

Output:
  ╔════════════════════════════════════════════════════════════════╗
  ║         RESUMO DA CONFIGURAÇÃO ATUAL (Carregadado do DB)      ║
  ╚════════════════════════════════════════════════════════════════╝
  
  📊 ESCALONAMENTO:
    • Limite de Falhas: 5
    • Workers: 2
    • Retry Delays: 5min → 15min → 60min → 240min
    • Tempo est. para 1000 itens: ~2.5h
  
  ...


✅ PRÓXIMOS PASSOS
═════════════════════════════════════════════════════════════════

1. Executar migrations
   $ python manage.py migrate

2. No Django Admin:
   Produtos → Configurações de Escalonamento
   
3. Revisar defaults e ajustar conforme ambiente (dev/staging/prod)

4. Documentar em "Notas" qualquer mudança realizada

5. Monitorado logs para ver se config está sendo aplicada


❓ FAQ
════════════════════════════════════════════════════════════════

P: "E se o banco cair em produção?"
R: Fallback para env vars. Certifique-se de ter variáveis de ambiente
   definidas no Cloud Run como backup.

P: "Como sincronizar config entre dev e prod?"
R: Export do admin em um DB, import no outro (Django dumpdata/loaddata).
   Ou clone config manualmente entre ambientes.

P: "Qual config recomenda para produção GCP?"
R:
   LIMITE_FALHAS=5     (nem muito alto, nem muito baixo)
   NUM_WORKERS=4-8     (depende do tamanho da máquina no Cloud Run)
   PLAYWRIGHT_TIMEOUT=30000ms  (padrão sensato)
   RATE_LIMIT_DELAY=300ms      (padrão sensato)
   LOG_LEVEL=INFO              (equilibrado)

P: "Como faço rollback se mudar algo errado?"
R: Campo "Notas" documenta histórico. Volta para o valor anterior no admin
   (ex: de num_workers=8 → 2 se detectar problema).
   Django não tem "versioning" de model changes,então use "Notas" para track.

P: "Múltiplas instâncias do Cloud Run compartilham a config certo?"
R: SIM! Todas apontam para o mesmo MySQL no Cloud SQL, então todas leem
   a mesma EscalonamentoConfig (pk=1).
