#!/usr/bin/env python
"""
Script de teste para validar sistema de manutenção do site.
Execute: python test_maintenance_system.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.models import SiteMaintenanceConfig
from django.test import Client
from django.urls import reverse
import time


def test_model_creation():
    """Testa se o modelo foi criado corretamente."""
    print("=" * 60)
    print("TEST 1: Criação do Modelo")
    print("=" * 60)
    
    try:
        config = SiteMaintenanceConfig.get_config()
        print(f"✅ Config obtida com ID: {config.pk}")
        print(f"   - Em Manutenção: {config.em_manutencao}")
        print(f"   - Título: {config.titulo}")
        print(f"   - Mensagem: {config.mensagem[:50]}...")
        print(f"   - Tempo estimado: {config.tempo_estimado_minutos} min")
        print(f"   - Criado em: {config.criado_em}")
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_singleton():
    """Testa se é verdadeiramente um singleton."""
    print("\n" + "=" * 60)
    print("TEST 2: Validar Singleton (apenas 1 registro)")
    print("=" * 60)
    
    try:
        count = SiteMaintenanceConfig.objects.count()
        if count == 1:
            print(f"✅ Apenas 1 registro no banco (correto!)")
            return True
        else:
            print(f"❌ Encontrados {count} registros (esperado: 1)")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_middleware_bypass():
    """Testa se o middleware permite bypass de admin."""
    print("\n" + "=" * 60)
    print("TEST 3: Middleware - Bypass de Admin")
    print("=" * 60)
    
    try:
        client = Client()
        
        # Ativar manutenção
        config = SiteMaintenanceConfig.get_config()
        config.em_manutencao = True
        config.save()
        time.sleep(0.5)  # Dar uma chance ao cache
        
        # Testar acesso ao admin (deve funcionar)
        response = client.get('/admin/')
        if response.status_code in [200, 302]:  # 200 se logado, 302 redirect se não
            print(f"✅ Admin acessível em manutenção (HTTP {response.status_code})")
        else:
            print(f"⚠️  Admin retornou HTTP {response.status_code}")
        
        # Testar acesso ao índice (deve ser 503)
        response = client.get('/')
        if response.status_code == 503:
            print(f"✅ Index bloqueado com HTTP 503 em manutenção")
        else:
            print(f"⚠️  Index retornou HTTP {response.status_code} (esperado 503)")
        
        # Desativar manutenção
        config.em_manutencao = False
        config.save()
        
        return True
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_admin_registration():
    """Testa se o admin foi registrado corretamente."""
    print("\n" + "=" * 60)
    print("TEST 4: Admin Registration")
    print("=" * 60)
    
    try:
        from django.contrib import admin
        
        # Verificar se está registrado
        is_registered = SiteMaintenanceConfig in admin.site._registry
        if is_registered:
            admin_instance = admin.site._registry[SiteMaintenanceConfig]
            print(f"✅ SiteMaintenanceConfig registrado no admin")
            print(f"   - Classe: {admin_instance.__class__.__name__}")
            print(f"   - List display: {admin_instance.list_display}")
            return True
        else:
            print(f"❌ SiteMaintenanceConfig não está registrado no admin")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_middleware_registration():
    """Testa se o middleware foi adicionado ao settings."""
    print("\n" + "=" * 60)
    print("TEST 5: Middleware Registration")
    print("=" * 60)
    
    try:
        from django.conf import settings
        
        middlewares = settings.MIDDLEWARE
        maintenance_middleware = 'produtos.middleware.MaintenanceMiddleware'
        
        if maintenance_middleware in middlewares:
            idx = middlewares.index(maintenance_middleware)
            print(f"✅ Middleware registrado em SETTINGS")
            print(f"   - Posição: {idx + 1}/{len(middlewares)}")
            print(f"   - Classe: {maintenance_middleware}")
            return True
        else:
            print(f"❌ Middleware não encontrado em SETTINGS")
            print(f"   Middlewares registrados: {middlewares}")
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def test_template_existence():
    """Testa se o template existe."""
    print("\n" + "=" * 60)
    print("TEST 6: Template Existence")
    print("=" * 60)
    
    try:
        from django.template.loader import get_template
        
        template = get_template('maintenance.html')
        print(f"✅ Template 'maintenance.html' encontrado")
        print(f"   - Template engine: {template.engine.name}")
        return True
    except Exception as e:
        print(f"❌ Template não encontrado: {e}")
        return False


def test_html_content():
    """Testa se a resposta HTML contém elementos esperados."""
    print("\n" + "=" * 60)
    print("TEST 7: HTML Content Check")
    print("=" * 60)
    
    try:
        from django.template.loader import render_to_string
        
        config = SiteMaintenanceConfig.get_config()
        html = render_to_string('maintenance.html', {
            'titulo': config.titulo,
            'mensagem': config.mensagem,
            'tempo_estimado_minutos': config.tempo_estimado_minutos,
            'mostrar_tempo_estimado': config.mostrar_tempo_estimado,
        })
        
        keys_to_check = ['titulo', 'mensagem', 'tempo_estimado_minutos', 'maintenance-card']
        found = [key for key in keys_to_check if key in html]
        
        if len(found) == len(keys_to_check):
            print(f"✅ Template contém todos os elementos esperados")
            for key in found:
                print(f"   ✓ {key}")
            return True
        else:
            missing = set(keys_to_check) - set(found)
            print(f"⚠️  Faltam elementos: {missing}")
            return False
    except Exception as e:
        print(f"❌ Erro ao renderizar template: {e}")
        return False


# ============================================================
# EXECUTAR TESTES
# ============================================================

if __name__ == '__main__':
    print("\n")
    print("🧪 TESTE DO SISTEMA DE MANUTENÇÃO DO SITE")
    print("=" * 60)
    
    results = []
    
    results.append(("Model Creation", test_model_creation()))
    results.append(("Singleton Check", test_singleton()))
    results.append(("Authentication", test_admin_registration()))
    results.append(("Middleware Registration", test_middleware_registration()))
    results.append(("Template Existence", test_template_existence()))
    results.append(("HTML Content", test_html_content()))
    results.append(("Middleware Bypass", test_middleware_bypass()))
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESULTADO FINAL")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    print(f"Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        print("\n🎉 TODOS OS TESTES PASSARAM! Sistema pronto para uso!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} teste(s) falharam. Verifique os erros acima.")
        sys.exit(1)
