"""Middleware para gerenciar modo de manutenção do site."""

from django.shortcuts import render
from django.http import HttpResponse
from django.utils.text import slugify
from django.core.exceptions import DisallowedHost
import logging

logger = logging.getLogger(__name__)


class HostValidationMiddleware:
    """
    Middleware que valida e registra hosts rejeitados ANTES do CommonMiddleware.
    Útil para debug em produção quando domínios não estão em ALLOWED_HOSTS.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        from django.conf import settings
        self.allowed_hosts = settings.ALLOWED_HOSTS
        
        logger.info(f"✅ HostValidationMiddleware inicializado")
        logger.info(f"   ALLOWED_HOSTS configurado com {len(self.allowed_hosts)} host(s)")
        for i, host in enumerate(self.allowed_hosts, 1):
            logger.info(f"   [{i}] {host}")
    
    def __call__(self, request):
        # Se ALLOWED_HOSTS está vazio ou rejeitar o host, logar informações úteis
        incoming_host = request.META.get('HTTP_HOST', 'UNKNOWN')
        
        from django.conf import settings
        
        if not self.allowed_hosts:
            logger.error(
                f"🚨 ALLOWED_HOSTS está VAZIO em produção (DEBUG={settings.DEBUG})!\n"
                f"   Host da requisição: {incoming_host}\n"
                f"   Esta requisição será rejeitada pelo CommonMiddleware"
            )
        elif incoming_host != 'UNKNOWN' and incoming_host not in self.allowed_hosts:
            # Host não está na whitelist - COLETAR INFORMAÇÕES DETALHADAS
            user_agent = request.META.get('HTTP_USER_AGENT', 'UNKNOWN')
            remote_addr = request.META.get('REMOTE_ADDR', 'UNKNOWN')
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', 'NONE')
            referer = request.META.get('HTTP_REFERER', 'NONE')
            method = request.method
            path = request.path
            query_string = request.META.get('QUERY_STRING', '')
            
            # Detectar se é requisição INTERNA ou EXTERNA
            eh_python_requests = 'python-requests' in user_agent.lower()
            eh_localhost = remote_addr in ['127.0.0.1', 'localhost', '0.0.0.0'] or 'localhost' in remote_addr
            eh_interno_gcp = remote_addr.startswith('10.') or remote_addr.startswith('172.')
            
            origem = "???"
            if eh_python_requests:
                origem = "🔴 INTERNO (python-requests)"
            elif eh_localhost:
                origem = "🔴 INTERNO (localhost)"
            elif eh_interno_gcp:
                origem = "🟡 GCP/INTERNO (IP privado)"
            else:
                origem = "🔵 EXTERNO (IP público/DNS)"
            
            logger.warning(
                f"⚠️ Host rejeitado (não está em ALLOWED_HOSTS) - {origem}:\n"
                f"   Host: {incoming_host}\n"
                f"   User-Agent: {user_agent[:80]}\n"
                f"   REMOTE_ADDR: {remote_addr}\n"
                f"   X-Forwarded-For: {x_forwarded_for}\n"
                f"   Method: {method} {path}\n"
                f"   Query: {query_string[:100] if query_string else 'NONE'}\n"
                f"   Referer: {referer if referer != 'NONE' else 'NONE'}\n"
                f"   ALLOWED_HOSTS: {self.allowed_hosts}\n"
                f"\n   💡 Solução: Adicione '{incoming_host}' à variável ALLOWED_HOSTS"
            )
        
        return self.get_response(request)


class MaintenanceMiddleware:
    """
    Middleware que intercepta requisições quando o site está em manutenção.
    
    Se SiteMaintenanceConfig.em_manutencao = True, renderiza template de manutenção
    em vez de processar a requisição normalmente.
    
    Exceções: Admin, API, static files, media são deixados passar.
    """
    
    # Rotas/padrões que permitem acesso mesmo em manutenção
    MAINTENANCE_BYPASS_PATHS = [
        '/admin/',           # Django admin
        '/api/',             # APIs (presumindo que começam com /api/)
        '/static/',          # CSS, JS, imagens
        '/media/',           # Média files
        '/favicon.ico',
        '/robots.txt',
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verificar se deve bypaxs (admin, API, static, media)
        if self._should_bypass(request.path):
            return self.get_response(request)
        
        # Verificar se site está em manutenção
        try:
            from .models import SiteMaintenanceConfig
            config = SiteMaintenanceConfig.get_config()
            
            if config.em_manutencao:
                # Renderizar página de manutenção
                return render(
                    request,
                    'maintenance.html',
                    {
                        'titulo': config.titulo,
                        'mensagem': config.mensagem,
                        'tempo_estimado_minutos': config.tempo_estimado_minutos,
                        'mostrar_tempo_estimado': config.mostrar_tempo_estimado,
                        'email_contato': config.email_contato,
                        'data_inicio': config.data_inicio,
                    },
                    status=503  # Service Unavailable
                )
        except Exception:
            # Se houver erro ao buscar config, deixar passar normalmente
            # (ex: migration em andamento, banco offline, etc)
            pass
        
        return self.get_response(request)
    
    def _should_bypass(self, path):
        """Verifica se o caminho deve ser ignorado (permitido mesmo em manutenção)."""
        for bypass_path in self.MAINTENANCE_BYPASS_PATHS:
            if path.startswith(bypass_path):
                return True
        return False
