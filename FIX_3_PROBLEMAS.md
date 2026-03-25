╔════════════════════════════════════════════════════════════════════════════════╗
║               3 PROBLEMAS RESOLVIDOS - SHOPEE, AMAZON, LOGOUT                  ║
╚════════════════════════════════════════════════════════════════════════════════╝


🔧 RESUMO DOS FIXES
═════════════════════════════════════════════════════════════════════════════════

❌ PROBLEMA 1: Shopee extrai apenas plataforma, resto dos campos vazios
   ✅ SOLUÇÃO: Novo scraper especializado _extrair_dados_shopee() com seletores CSS

❌ PROBLEMA 2: Amazon (amzn.to) dá erro 500
   ✅ SOLUÇÃO: 
      - Aumentar timeout de 30s → 45s para URLs encurtadas
      - Melhor error handling (não faz raise, retorna dados)
      - Detecta robot/captcha block

❌ PROBLEMA 3: Falta timeout de logout
   ✅ SOLUÇÃO: Novo campo session_timeout_minutos na EscalonamentoConfig


🚀 APLICAR AGORA (5 MIN)
═════════════════════════════════════════════════════════════════════════════════

PASSO 1: Criar (ou escreve o nome correto de) migration
  $ python manage.py makemigrations produtos

  Esperado:
    Migrations for 'produtos':
      0008_escalonamentoconfig_session_timeout.py - Add field session_timeout_minutos

PASSO 2: Aplicar migrations
  $ python manage.py migrate

  Esperado:
    Applying produtos.0008_escalonamentoconfig_session_timeout... OK

PASSO 3: Testar no admin
  $ python manage.py runserver
  
  Abrir: http://localhost:8000/admin/
  Ir para: Produtos → Configuração de Escalonamento
  
  Procurar por:
    1. ✅ Nova aba "🔐 SEGURANÇA" com campo "Timeout de Logout (minutos)"
    2. Valor default: 30 minutos
    3. Help text explicativo


📊 DETALHES DO FIX #1: Shopee
═════════════════════════════════════════════════════════════════════════════════

ANTES:
  ➖ Shopee usava scraper GENÉRICO (só meta tags)
  ➖ Meta tags geralmente vazias em Shopee
  ➖ Resultado: apenas "plataforma" era extraída, resto vazio

AGORA:
  ✅ Nova função _extrair_dados_shopee() com seletores CSS específicos
  ✅ Extrai: título, preço, preço original, imagem, descrição, categoria
  ✅ Fallback automático para meta tags se seletores não funcionem
  ✅ Melhora qualidade de imagem (w94_h94 → w500_h500)

TESTE:
  Link: https://s.shopee.com.br/2LToEqKjC
  Resultado esperado: Todos os campos preenchidos ✓


📊 DETALHES DO FIX #2: Amazon
═════════════════════════════════════════════════════════════════════════════════

ANTES:
  ❌ Erro 500 em amzn.to (URL encurtada)
  ❌ Timeout erro no raise() causava traverso completo

AGORA:
  ✅ Timeout aumentado: 30s → 45s (para URLs encurtadas)
  ✅ Melhor logging de erro_extracao (não propaga, retorna dados)
  ✅ Detecta robot/captcha block da Amazon e retorna erro específico
  ✅ Admin não trava mais (erro retorna gracefully)

TESTE:
  Link: https://amzn.to/486LO0W
  Resultado esperado: Extrai dados SEM erro 500 ✓


📊 DETALHES DO FIX #3: Logout Timeout
═════════════════════════════════════════════════════════════════════════════════

NOVO CAMPO: session_timeout_minutos
  • Armazenado no banco (EscalonamentoConfig)
  • Editável via Django Admin
  • Padrão: 30 minutos
  • Sem necessidade de redeploy para mudar

COMO FUNCIONA:
  1. Admin edita session_timeout_minutos (ex: 60 minutos)
  2. config_escalonamento.py carrega do BD
  3. settings.py usa SESSION_COOKIE_AGE = 60 * 60 segundos
  4. Django força logout automaticamente após 60 min inatividade

EDITAR NO ADMIN:
  Admin → Produtos → Configuração de Escalonamento
  Seção: 🔐 SEGURANÇA
  Campo: "Timeout de Logout (minutos)"
  Default: 30 (recomendado)
  
  Opções comuns:
    ⏱️ 15 min = muito seguro, logout frequente
    ⏱️ 30 min = equilíbrio (recomendado)
    ⏱️ 60 min = mais conveniente, menos seguro
    ⏱️ 120 min = muito longo para produção


✅ VALIDAR APÓS APLICAR
═════════════════════════════════════════════════════════════════════════════════

1. SHOPEE: Testar extração
   Link: https://s.shopee.com.br/2LToEqKjC
   Esperado: Título, Preço, Imagem, Descrição, Categoria → TODOS PREENCHIDOS

2. AMAZON: Testar URL encurtada
   Link: https://amzn.to/486LO0W
   Esperado: SEM erro 500 (pode ter dados parciais, mas não trava)

3. LOGOUT: Testar timeout
   Fazer login → Deixar inativo 31 minutos → Reload
   Esperado: Logout automático (volta para login)


🔍 DEBUG
═════════════════════════════════════════════════════════════════════════════════

Se Shopee ainda não extrair:
  $ python manage.py shell
  >>> from produtos.scraper import _extrair_dados_shopee
  >>> asyncio.run(_extrair_dados_shopee('https://s.shopee.com.br/2LToEqKjC'))
  # Checar output

Se Amazon continuar dando erro:
  $ python manage.py shell
  >>> from produtos.scraper import _extrair_dados_amazon
  >>> asyncio.run(_extrair_dados_amazon('https://amzn.to/486LO0W'))
  # Check logs

Se SESSION_COOKIE_AGE não funcionar:
  $ python manage.py shell
  >>> from django.conf import settings
  >>> print(f"SESSION_COOKIE_AGE: {settings.SESSION_COOKIE_AGE} segundos")
  >>> print(f"Equivalente: {settings.SESSION_COOKIE_AGE / 60} minutos")


📝 NOTAS IMPORTANTES
═════════════════════════════════════════════════════════════════════════════════

1. SHOPEE:
   - Seletores CSS podem mudar se Shopee redesenhar site
   - Se parar de funcionar, verificar console.log no Playwright

2. AMAZON:
   - amzn.to redirecionamentos às vezes demoram (por isso 45s)
   - Bot check: descomentar em logs se estiver muito frequente

3. LOGOUT:
   - SESSION_EXPIRE_AT_BROWSER_CLOSE = True (logout ao fechar aba)
   - SESSION_COOKIE_HTTPONLY = True (proteção contra XSS)
   - SESSION_COOKIE_SECURE = não DEBUG (HTTPS em produção)


✨ PRÓXIMA ETAPA
═════════════════════════════════════════════════════════════════════════════════

Após validar os 3 fixes, você está pronto para:
  ✓ Testar com 100+ produtos Shopee/Amazon
  ✓ Considerar Phase 3: ThreadPoolExecutor para paralelismo
  ✓ Deploy em GCP Cloud Run


Alguma dúvida? 🤔
