"""
Configurações Escaláveis para Processamento de 1000+ Produtos
Carrega de: 1. Banco de Dados (Django ORM) 2. Variáveis de Ambiente 3. Defaults
Sem necessidade de redeploy para ajustar em runtime.
"""

from datetime import timedelta
import os
import logging

logger = logging.getLogger(__name__)

# ============================================================================
# FUNÇÃO PARA CARREGAR CONFIG DO BANCO (com fallback para env)
# ============================================================================

def _load_config_from_db_or_env(field_name: str, default_value, cast_type=None):
    """
    Carrega configuração em ordem: DB → Env Vars → Default
    
    Args:
        field_name: Nome do campo no modelo (ex: 'limite_falhas')
        default_value: Valor padrão se tudo falhar
        cast_type: Tipo para converter (int, bool, str)
    
    Returns:
        Valor da config (do banco, env var, ou default)
    """
    # Tentar carregar do banco de dados primeiro
    try:
        from .models import EscalonamentoConfig
        config = EscalonamentoConfig.obter_config()
        db_value = getattr(config, field_name, None)
        if db_value is not None:
            return db_value
    except Exception as e:
        # Banco pode não ter migrado ainda (dev local), ignora
        logger.debug(f"Não consegui carregar {field_name} do DB: {e}")
    
    # Tentar variável de ambiente (with naming convention)
    env_key = field_name.upper()
    if env_key in os.environ:
        env_value = os.environ[env_key]
        if cast_type:
            try:
                return cast_type(env_value)
            except (ValueError, TypeError):
                logger.warning(f"Falha ao converter {env_key}={env_value} para {cast_type.__name__}")
        else:
            return env_value
    
    # Retorna default
    return default_value


# ============================================================================
# CONFIGURAÇÕES DE ESCALONAMENTO
# ============================================================================

LIMITE_FALHAS = _load_config_from_db_or_env('limite_falhas', 5, int)

# Delays de retry com backoff exponencial
# Get individual retry delays from DB or env
retry_1 = _load_config_from_db_or_env('retry_delay_1_minutos', 5, int)
retry_2 = _load_config_from_db_or_env('retry_delay_2_minutos', 15, int)
retry_3 = _load_config_from_db_or_env('retry_delay_3_minutos', 60, int)
retry_4 = _load_config_from_db_or_env('retry_delay_4_minutos', 240, int)

RETRY_DELAYS = [
    timedelta(minutes=retry_1),
    timedelta(minutes=retry_2),
    timedelta(hours=1) if retry_3 == 60 else timedelta(minutes=retry_3),
    timedelta(hours=4) if retry_4 == 240 else timedelta(minutes=retry_4),
]

# ============================================================================
# CONFIGURAÇÕES DE FILA E PROCESSAMENTO
# ============================================================================

NUM_WORKERS = _load_config_from_db_or_env('num_workers', 2, int)
MAX_QUEUE_SIZE = _load_config_from_db_or_env('max_queue_size', 5000, int)
TASK_TIMEOUT = _load_config_from_db_or_env('task_timeout_segundos', 120, int)
RATE_LIMIT_DELAY_MS = _load_config_from_db_or_env('rate_limit_delay_ms', 300, int)
MAX_CONCURRENT_REQUESTS = _load_config_from_db_or_env('max_concurrent_requests', 2, int)

# ============================================================================
# CONFIGURAÇÕES DE BANCO DE DADOS
# ============================================================================

USE_SQLITE = _load_config_from_db_or_env('use_sqlite', False, lambda x: x.lower() == 'true' if isinstance(x, str) else x)
SQLITE_TIMEOUT = _load_config_from_db_or_env('sqlite_timeout_segundos', 60, int)
MYSQL_CONN_MAX_AGE = int(os.getenv('MYSQL_CONN_MAX_AGE', '600'))
MYSQL_POOL_SIZE = int(os.getenv('MYSQL_POOL_SIZE', '10'))

# ============================================================================
# CONFIGURAÇÕES DE PLAYWRIGHT (SCRAPING)
# ============================================================================

PLAYWRIGHT_TIMEOUT_MS = _load_config_from_db_or_env('playwright_timeout_ms', 30000, int)
PLAYWRIGHT_PAGE_DELAY_MS = _load_config_from_db_or_env('playwright_delay_ms', 3000, int)

# ============================================================================
# CONFIGURAÇÕES DE MANAGEMENT COMMAND
# ============================================================================

CMD_BATCH_SIZE = int(os.getenv('CMD_BATCH_SIZE', '500'))
CMD_TIMEOUT_MINUTES = int(os.getenv('CMD_TIMEOUT_MINUTES', '15'))

# ============================================================================
# CONFIGURAÇÕES DE LOGGING
# ============================================================================

LOG_LEVEL = _load_config_from_db_or_env('log_level', 'INFO', str)
LOGS_RETENTION_DAYS = _load_config_from_db_or_env('logs_retention_dias', 30, int)

# ============================================================================
# CONFIGURAÇÕES DE CELERY (OPCIONAL)
# ============================================================================

USE_CELERY = os.getenv('USE_CELERY', 'False').lower() == 'true'
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
CELERY_WORKERS = int(os.getenv('CELERY_WORKERS', '4'))
CELERY_MAX_RETRIES = int(os.getenv('CELERY_MAX_RETRIES', '5'))

# ============================================================================
# VARIÁVEIS CALCULADAS (NÃO MODIFICAR)
# ============================================================================

OPERATION_MODE = os.getenv('OPERATION_MODE', 'development')
ESTIMATED_TIME_1000_PRODUCTS_HOURS = round(1000 * 30 / (60 * NUM_WORKERS), 1)


# ============================================================================
# FUNÇÕES DE UTILIDADE
# ============================================================================

def get_retry_delay(falha_numero: int) -> timedelta:
    """
    Retorna o delay para retry baseado no número da falha.
    
    Args:
        falha_numero: Número da falha (1-LIMITE_FALHAS)
    
    Returns:
        timedelta com delay até próxima tentativa
    """
    if falha_numero <= 0 or falha_numero > len(RETRY_DELAYS):
        return timedelta(days=365)  # "nunca" (desativado)
    return RETRY_DELAYS[falha_numero - 1]


def get_config_info() -> str:
    """
    Retorna string formatada com resumo das configurações.
    Usado no admin para previewar config.
    """
    info = f"""
╔════════════════════════════════════════════════════════════════╗
║         RESUMO DA CONFIGURAÇÃO ATUAL (Carregadado do DB)      ║
╚════════════════════════════════════════════════════════════════╝

📊 ESCALONAMENTO:
  • Limite de Falhas: {LIMITE_FALHAS}
  • Workers: {NUM_WORKERS}
  • Retry Delays: {retry_1}min → {retry_2}min → {retry_3}min → {retry_4}min
  • Tempo est. para 1000 itens: ~{ESTIMATED_TIME_1000_PRODUCTS_HOURS}h

🎪 FILA:
  • Max Queue Size: {MAX_QUEUE_SIZE}
  • Task Timeout: {TASK_TIMEOUT}s
  • Rate Limit Delay: {RATE_LIMIT_DELAY_MS}ms
  • Max Concurrent: {MAX_CONCURRENT_REQUESTS}

💾 DATABASE:
  • Usar SQLite: {USE_SQLITE}
  • SQLite Timeout: {SQLITE_TIMEOUT}s
  • MySQL Pool: {MYSQL_POOL_SIZE}

🌐 PLAYWRIGHT:
  • Timeout: {PLAYWRIGHT_TIMEOUT_MS}ms
  • Delay entre páginas: {PLAYWRIGHT_PAGE_DELAY_MS}ms

📋 LOGGING:
  • Level: {LOG_LEVEL}
  • Retenção: {LOGS_RETENTION_DAYS} dias

⚙️  MODO: {OPERATION_MODE}
    """
    return info


def get_config_summary() -> dict:
    """Retorna dicionário com configurações principais (para logs/debug)."""
    return {
        'environment': OPERATION_MODE,
        'workers': NUM_WORKERS,
        'limite_falhas': LIMITE_FALHAS,
        'max_queue_size': MAX_QUEUE_SIZE,
        'rate_limit_ms': RATE_LIMIT_DELAY_MS,
        'playwright_timeout_ms': PLAYWRIGHT_TIMEOUT_MS,
        'estimated_1000_products_hours': ESTIMATED_TIME_1000_PRODUCTS_HOURS,
        'use_celery': USE_CELERY,
        'log_level': LOG_LEVEL,
    }

