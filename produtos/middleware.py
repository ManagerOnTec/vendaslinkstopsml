"""Middleware para gerenciar modo de manutenção do site."""

from django.shortcuts import render
from django.http import HttpResponse
from django.utils.text import slugify


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
