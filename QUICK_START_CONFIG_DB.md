╔════════════════════════════════════════════════════════════════════════════════╗
║          GUIA RÁPIDO: Nova Solução com Banco de Dados (5 MIN)                 ║
╚════════════════════════════════════════════════════════════════════════════════╝


✅ MUDANÇAS IMPLEMENTADAS
═════════════════════════════════════════════════════════════════════════════════

1️⃣  models.py
    └─ Novo modelo: EscalonamentoConfig (singleton no banco)
    └─ 20+ campos com help_text explicativo
    └─ Automático: EscalonamentoConfig.obter_config()

2️⃣  admin.py
    └─ Admin customizado com fieldsets agrupados por categoria
    └─ Readonly: atualizado_em, config_summary (preview)
    └─ Proibido: add/delete (singleton protection)
    └─ Solo edit permitido (modificar pk=1)

3️⃣  config_escalonamento.py [REFATORADO]
    └─ Função _load_config_from_db_or_env() com prioridade:
       Bank → Env Vars → Defaults
    └─ Fallback automático se banco não estiver acessível
    └─ get_config_info() para preview no admin

4️⃣  Migrations
    └─ 0005_escalonamentoconfig.py (criada)
    └─ Pronta para rodar


🚀 EXECUTAR AGORA (5 MIN)
═════════════════════════════════════════════════════════════════════════════════

PASSO 1: Aplicar Migrations
  $ python manage.py migrate produtos

  Esperado:
    Applying produtos.0005_escalonamentoconfig... OK


PASSO 2: Testar Carregamento
  $ python manage.py shell
  >>> from produtos.config_escalonamento import get_config_summary
  >>> print(get_config_summary())

  Esperado:
    {
      'environment': 'development',
      'workers': 2,
      'limite_falhas': 5,
      ...
    }


PASSO 3: Acessar Admin
  1. Abrir: http://localhost:8000/admin/
  2. Loguinput
  3. Ir para: Produtos → Configuração de Escalonamento
  4. Clicar no único registro para editar


🎯 PRÓXIMA ALTERAÇÃO (via Admin)
═════════════════════════════════════════════════════════════════════════════════

Para mudar LIMITE_FALHAS (ex. aumentar de 5 para 7):

  1. Admin → Produtos → Configuração de Escalonamento
  2. Limite de Falhas Consecutivas: 5 → 7
  3. Campo "Notas": adicionar motivo da mudança
  4. Salvar

  ✨ Resultado: Próxima tarefa de scraper usa novo valor


📋 COMPARAÇÃO: ANTES vs DEPOIS
═════════════════════════════════════════════════════════════════════════════════

Cenário: Aumentar NUM_WORKERS de 2 para 4 em produção

ANTES (decouple + .env):
  1. Editar arquivo .env
  2. fazer git commit
  3. Deploy via CI/CD
  4. Aguarde build + rollout
  Tempo: 30-60 minutos ⏱️

DEPOIS (banco + admin):
  1. Abrir Django Admin
  2. Editar campo
  3. Clicar Salvar
  4. Próxima iteração usa novo valor
  Tempo: 2 minutos ⚡


🔧 CUSTOMIZAÇÕES (Opcional)
═════════════════════════════════════════════════════════════════════════════════

Se quiser FORÇAR um valor via env var (ignorar o banco):

  Editar produtos/config_escalonamento.py, função _load_config_from_db_or_env():

  # Descomentar esta seção para priorizar env vars sobre banco:
  # if env_key in os.environ:
  #     return cast_type(os.environ[env_key])  # Retorna antes de consultar DB


Se quiser adicionar mais campos à config:

  1. Adicionar campo em models.EscalonamentoConfig
  2. Criar migration: python manage.py makemigrations
  3. Aplicar: python manage.py migrate
  4. Campo aparece automaticamente no admin


💾 PERSISTÊNCIA E SEGURANÇA
═════════════════════════════════════════════════════════════════════════════════

✅ Dados salvos em: MySQL Cloud SQL (GCP)
✅ Única instância: pk=1 (model.save() força pk=1)
✅ Backup automático: Via GCP Cloud SQL backups
✅ Acesso: Apenas Django superusers via admin
✅ Auditoria: Campo "nota" documenta histórico


❓ PERGUNTAS COMUNS
═════════════════════════════════════════════════════════════════════════════════

P: "E se mudar config enquanto uma tarefa está rodando?"
R: Config é lida NO INÍCIO de cada tarefa. Mudanças pegam efeito na próxima.

P: "Posso voltar a usar .env?"
R: SIM. Se comentar banco lookup em _load_config_from_db_or_env(),
   volta a usar env vars como antes.

P: "Cloud Run vai quebrar sem .env?"
R: NÃO. Sistema tenta DB→Env→Defaults. Se tudo falhar, usa defaults.

P: "Posso ter configs diferentes para dev/staging/prod?"
R: Com banco único, não. Soluções:
   - Usar 3 bancos separados (recomendado)
   - Usar django-environ para caregar DB_HOST do env var


📞 SUPORTE
═════════════════════════════════════════════════════════════════════════════════

Arquivo de referência: CONFIG_BANCO_DADOS.md (leia para detalhes)

Debug:
  $ python manage.py shell
  >>> from produtos.config_escalonamento import get_config_info
  >>> print(get_config_info())


✨ PRONTO!
═════════════════════════════════════════════════════════════════════════════════

✅ Migrations criadas e prontas
✅ Admin configurado e customizado
✅ config_escalonamento.py refatorado com fallback
✅ Sem mais .env complicados
✅ Edições em tempo real via admin
✅ Compatível com GCP Cloud Run

Próximo passo: python manage.py migrate
