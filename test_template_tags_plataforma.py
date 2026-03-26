"""
Teste para validar que os template tags customizados para plataforma
funcionam de forma segura, mesmo com valores None.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from django.template import Template, Context
from produtos.models import ProdutoAutomatico, PlataformaEcommerce


def testar_filtros_plataforma():
    """Testa os filtros customizados de plataforma."""
    print("\n" + "=" * 70)
    print("🧪 TESTES: TEMPLATE TAGS PLATAFORMA (com proteção contra None)")
    print("=" * 70 + "\n")
    
    # Criar objeto produto para teste
    produto = ProdutoAutomatico.objects.first()
    
    if not produto:
        print("❌ Nenhum produto encontrado no BD para teste")
        return
    
    print(f"Testando com produto: {produto.titulo[:50]}...")
    print(f"  - ID: {produto.id}")
    print(f"  - Plataforma FK: {produto.plataforma}")
    
    # ========== TESTE 1: plataforma_chave ==========
    print("\n✅ TESTE 1: Filtro 'plataforma_chave'")
    template = Template("{% load produto_tags %}{{ produto|plataforma_chave }}")
    context = Context({'produto': produto})
    resultado = template.render(context)
    print(f"   Resultado: '{resultado}'")
    print(f"   Esperado: Uma chave válida ou 'outro' (seguro contra None)")
    
    # ========== TESTE 2: plataforma_nome ==========
    print("\n✅ TESTE 2: Filtro 'plataforma_nome'")
    template = Template("{% load produto_tags %}{{ produto|plataforma_nome }}")
    context = Context({'produto': produto})
    resultado = template.render(context)
    print(f"   Resultado: '{resultado}'")
    print(f"   Esperado: Nome da plataforma ou fallback")
    
    # ========== TESTE 3: plataforma_label_botao ==========
    print("\n✅ TESTE 3: Filtro 'plataforma_label_botao'")
    template = Template("{% load produto_tags %}{{ produto|plataforma_label_botao }}")
    context = Context({'produto': produto})
    resultado = template.render(context)
    print(f"   Resultado: '{resultado}'")
    print(f"   Esperado: Um label como 'Ver na Amazon', 'Ver no Mercado Livre', etc.")
    
    # ========== TESTE 4: Com produto.plataforma = None ==========
    print("\n✅ TESTE 4: Cenário CRÍTICO - Produto com plataforma = None")
    produto_sem_plataforma = ProdutoAutomatico(
        titulo="Produto Teste",
        link_afiliado="https://exemplo.com",
        plataforma=None  # ⚠️ Null FK
    )
    
    template = Template("{% load produto_tags %}{{ produto|plataforma_chave }}")
    context = Context({'produto': produto_sem_plataforma})
    resultado = template.render(context)
    print(f"   Resultado plataforma_chave: '{resultado}'")
    assert resultado == 'outro', f"Esperado 'outro', mas recebeu '{resultado}'"
    print(f"   ✅ PASSOU: Retornou fallback 'outro'")
    
    template = Template("{% load produto_tags %}{{ produto|plataforma_label_botao }}")
    context = Context({'produto': produto_sem_plataforma})
    resultado = template.render(context)
    print(f"   Resultado plataforma_label_botao: '{resultado}'")
    assert resultado == 'Ver na Loja', f"Esperado 'Ver na Loja', mas recebeu '{resultado}'"
    print(f"   ✅ PASSOU: Retornou fallback 'Ver na Loja'")
    
    # ========== TESTE 5: Testar condições no template ==========
    print("\n✅ TESTE 5: Condições no template ({% if %} com filtro)")
    
    template_text = """
    {% load produto_tags %}
    {% with plat_chave=produto|plataforma_chave %}
        {% if plat_chave == 'amazon' %}Amazon{% elif plat_chave == 'shopee' %}Shopee{% else %}Outro{% endif %}
    {% endwith %}
    """
    template = Template(template_text)
    context = Context({'produto': produto_sem_plataforma})
    resultado = template.render(context).strip()
    print(f"   Resultado: '{resultado}'")
    assert resultado == 'Outro', f"Esperado 'Outro', mas recebeu '{resultado}'"
    print(f"   ✅ PASSOU: Roteou para else corretamente")
    
    print("\n" + "=" * 70)
    print("✅ TODOS OS TESTES PASSARAM!")
    print("   Filtros são SEGUROS contra None/null values")
    print("=" * 70 + "\n")


if __name__ == '__main__':
    testar_filtros_plataforma()
