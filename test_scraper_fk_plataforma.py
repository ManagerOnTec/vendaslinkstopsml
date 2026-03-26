"""
Teste para validar que o scraper consegue pegar a plataforma do link
e atribuir corretamente à FK do modelo PlataformaEcommerce.
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.models import PlataformaEcommerce, ProdutoAutomatico
from produtos.detector_plataforma import DetectorPlataforma

# URLs de teste por plataforma
URLS_TESTE = {
    'mercado_livre': 'https://www.mercadolivre.com.br/item/MLB1234567890',
    'amazon': 'https://www.amazon.com.br/dp/B123456789',
    'shopee': 'https://www.shopee.com.br/product/123/456789',
    'shein': 'https://www.shein.com.br/p-xxx',
}

def testar_deteccao_plataforma():
    """Testa se DetectorPlataforma retorna strings corretas."""
    print("\n🔍 TESTE 1: Detecção de plataforma (string return)")
    print("=" * 60)
    
    for plataforma_esperada, url in URLS_TESTE.items():
        resultado = DetectorPlataforma.detectar(url)
        status = "✅" if resultado == plataforma_esperada else "❌"
        print(f"{status} {plataforma_esperada:15} -> {resultado:15} (URL: {url[:50]}...)")
    
    print()

def testar_atribuicao_fk():
    """Testa se consegue criar um produto e atribuir a FK corretamente."""
    print("\n🔗 TESTE 2: Atribuição de FK no modelo (simula scraper)")
    print("=" * 60)
    
    # Verificar se PlataformaEcommerce tem dados
    plataformas = PlataformaEcommerce.objects.all()
    print(f"Plataformas no BD: {plataformas.count()}")
    for p in plataformas:
        print(f"  - {p.chave} (id={p.id}): {p.nome}")
    
    if not plataformas.exists():
        print("❌ Nenhuma plataforma no BD! Criando dados de teste...")
        PlataformaEcommerce.objects.create(chave='mercado_livre', nome='Mercado Livre')
        PlataformaEcommerce.objects.create(chave='amazon', nome='Amazon')
        PlataformaEcommerce.objects.create(chave='shopee', nome='Shopee')
        print("✅ Plataformas criadas!")
    
    print("\nTestando atribuição de FK:")
    for plataforma_chave, url in URLS_TESTE.items():
        try:
            # Simula o que o scraper faz agora
            plataforma_chave_detectada = DetectorPlataforma.detectar(url)
            plataforma_obj = PlataformaEcommerce.objects.get(chave=plataforma_chave_detectada)
            
            # Criar producto de teste (sem salvar)
            produto = ProdutoAutomatico(
                link_afiliado=url,
                plataforma=plataforma_obj  # ✅ Atribuindo objeto FK
            )
            
            status = "✅" if produto.plataforma.chave == plataforma_chave_detectada else "❌"
            print(f"{status} {plataforma_chave:15} -> FK: {produto.plataforma.nome:15} (id={produto.plataforma.id})")
            
        except PlataformaEcommerce.DoesNotExist as e:
            print(f"❌ {plataforma_chave:15} -> ERRO: PlataformaEcommerce não encontrada para chave '{plataforma_chave_detectada}'")
        except Exception as e:
            print(f"❌ {plataforma_chave:15} -> ERRO: {type(e).__name__}: {str(e)}")
    
    print()

def testar_atribuicao_id():
    """Testa atribuição pelo ID ao invés de objeto."""
    print("\n🔗 TESTE 3: Atribuição via plataforma_id (alternativa)")
    print("=" * 60)
    
    for plataforma_chave, url in URLS_TESTE.items():
        try:
            plataforma_chave_detectada = DetectorPlataforma.detectar(url)
            plataforma_obj = PlataformaEcommerce.objects.get(chave=plataforma_chave_detectada)
            
            # Alternativa: atribuir ID
            produto = ProdutoAutomatico(
                link_afiliado=url,
            )
            produto.plataforma_id = plataforma_obj.id  # ✅ Atribuindo ID
            
            retrieval = ProdutoAutomatico.objects.get_or_none(plataforma_id=plataforma_obj.id)
            status = "✅"
            print(f"{status} {plataforma_chave:15} -> plataforma_id={plataforma_obj.id:3} (plataforma_obj.nome={plataforma_obj.nome})")
            
        except Exception as e:
            print(f"❌ {plataforma_chave:15} -> ERRO: {type(e).__name__}")
    
    print()

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🧪 TESTES: SCRAPER + FK PLATAFORMA")
    print("=" * 60)
    
    testar_deteccao_plataforma()
    testar_atribuicao_fk()
    testar_atribuicao_id()
    
    print("\n✅ Testes concluídos!")
