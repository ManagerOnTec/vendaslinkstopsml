from django.conf import settings


def site_settings(request):
    """Disponibiliza variáveis do site em todos os templates."""
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_DESCRIPTION': settings.SITE_DESCRIPTION,
        'GOOGLE_ADSENSE_ID': settings.GOOGLE_ADSENSE_ID,
    }
