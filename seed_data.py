"""
Script para popular o banco de dados com dados de demonstração.
Execute com: python manage.py shell < seed_data.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vendaslinkstopsml.settings')
django.setup()

from produtos.models import Categoria, Produto, Anuncio

# Criar Categorias
categorias_data = [
    {'nome': 'Eletrônicos', 'ordem': 1},
    {'nome': 'Casa e Decoração', 'ordem': 2},
    {'nome': 'Esportes', 'ordem': 3},
    {'nome': 'Moda', 'ordem': 4},
    {'nome': 'Informática', 'ordem': 5},
    {'nome': 'Celulares', 'ordem': 6},
]

categorias = {}
for cat_data in categorias_data:
    cat, created = Categoria.objects.get_or_create(
        nome=cat_data['nome'],
        defaults={'ordem': cat_data['ordem']}
    )
    categorias[cat_data['nome']] = cat
    status = 'Criada' if created else 'Já existe'
    print(f"  Categoria: {cat.nome} - {status}")

# Criar Produtos de Demonstração
produtos_data = [
    {
        'titulo': 'Fone de Ouvido Bluetooth TWS com Cancelamento de Ruído',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_917128-MLU75235241498_032024-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-1',
        'preco': 'R$ 89,90',
        'preco_original': 'R$ 149,90',
        'categoria': 'Eletrônicos',
        'destaque': True,
        'ordem': 1,
    },
    {
        'titulo': 'Smart TV 50" 4K UHD LED com Wi-Fi Integrado',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_918444-MLU74656498914_022024-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-2',
        'preco': 'R$ 1.899,00',
        'preco_original': 'R$ 2.499,00',
        'categoria': 'Eletrônicos',
        'destaque': True,
        'ordem': 2,
    },
    {
        'titulo': 'Notebook Gamer 15.6" Intel Core i5 8GB RAM SSD 512GB',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_649997-MLU74127553912_012024-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-3',
        'preco': 'R$ 3.299,00',
        'preco_original': 'R$ 4.199,00',
        'categoria': 'Informática',
        'destaque': True,
        'ordem': 3,
    },
    {
        'titulo': 'Smartwatch Relógio Inteligente com Monitor Cardíaco',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_652157-MLU72549498498_112023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-4',
        'preco': 'R$ 129,90',
        'preco_original': 'R$ 199,90',
        'categoria': 'Eletrônicos',
        'destaque': False,
        'ordem': 4,
    },
    {
        'titulo': 'Câmera de Segurança Wi-Fi Full HD com Visão Noturna',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_773679-MLU72017213521_102023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-5',
        'preco': 'R$ 79,90',
        'preco_original': 'R$ 129,90',
        'categoria': 'Eletrônicos',
        'destaque': False,
        'ordem': 5,
    },
    {
        'titulo': 'Cadeira Gamer Ergonômica com Apoio Lombar',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_889416-MLU72549498502_112023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-6',
        'preco': 'R$ 599,90',
        'preco_original': 'R$ 899,90',
        'categoria': 'Informática',
        'destaque': False,
        'ordem': 6,
    },
    {
        'titulo': 'Tênis Esportivo Masculino Running Ultra Leve',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_813443-MLU72549498506_112023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-7',
        'preco': 'R$ 159,90',
        'preco_original': 'R$ 249,90',
        'categoria': 'Esportes',
        'destaque': False,
        'ordem': 7,
    },
    {
        'titulo': 'Aspirador de Pó Robô Inteligente com Mapeamento',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_612917-MLU74127553916_012024-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-8',
        'preco': 'R$ 899,00',
        'preco_original': 'R$ 1.299,00',
        'categoria': 'Casa e Decoração',
        'destaque': True,
        'ordem': 8,
    },
    {
        'titulo': 'Smartphone 128GB 6.5" Câmera Tripla 48MP',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_949557-MLA74656498918_022024-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-9',
        'preco': 'R$ 1.199,00',
        'preco_original': 'R$ 1.699,00',
        'categoria': 'Celulares',
        'destaque': True,
        'ordem': 9,
    },
    {
        'titulo': 'Kit Halteres Emborrachados 20kg com Barra',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_773679-MLU72017213521_102023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-10',
        'preco': 'R$ 189,90',
        'preco_original': 'R$ 279,90',
        'categoria': 'Esportes',
        'destaque': False,
        'ordem': 10,
    },
    {
        'titulo': 'Luminária LED de Mesa com Carregador Wireless',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_889416-MLU72549498502_112023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-11',
        'preco': 'R$ 119,90',
        'categoria': 'Casa e Decoração',
        'destaque': False,
        'ordem': 11,
    },
    {
        'titulo': 'Mochila Notebook 15.6" Impermeável com USB',
        'imagem_url': 'https://http2.mlstatic.com/D_NQ_NP_2X_652157-MLU72549498498_112023-F.webp',
        'link_afiliado': 'https://mercadolivre.com.br/produto-exemplo-12',
        'preco': 'R$ 89,90',
        'preco_original': 'R$ 139,90',
        'categoria': 'Moda',
        'destaque': False,
        'ordem': 12,
    },
]

for prod_data in produtos_data:
    cat_nome = prod_data.pop('categoria')
    prod_data['categoria'] = categorias.get(cat_nome)
    prod, created = Produto.objects.get_or_create(
        titulo=prod_data['titulo'],
        defaults=prod_data
    )
    status = 'Criado' if created else 'Já existe'
    print(f"  Produto: {prod.titulo[:50]}... - {status}")

# Criar Anúncios de Exemplo
anuncios_data = [
    {
        'nome': 'Banner Topo - AdSense',
        'codigo_html': '<div style="background:#e3f2fd;padding:20px;border-radius:12px;text-align:center;color:#1565c0;font-weight:500;"><i class="bi bi-megaphone-fill me-2"></i>Espaço reservado para Google AdSense - Topo</div>',
        'posicao': 'topo',
        'ativo': True,
        'ordem': 1,
    },
    {
        'nome': 'Banner Meio - AdSense',
        'codigo_html': '<div style="background:#fff3e0;padding:15px;border-radius:12px;text-align:center;color:#e65100;font-weight:500;"><i class="bi bi-megaphone-fill me-2"></i>Espaço reservado para Google AdSense - Entre Produtos</div>',
        'posicao': 'meio',
        'ativo': True,
        'ordem': 1,
    },
    {
        'nome': 'Banner Rodapé - AdSense',
        'codigo_html': '<div style="background:#e8f5e9;padding:20px;border-radius:12px;text-align:center;color:#2e7d32;font-weight:500;"><i class="bi bi-megaphone-fill me-2"></i>Espaço reservado para Google AdSense - Rodapé</div>',
        'posicao': 'rodape',
        'ativo': True,
        'ordem': 1,
    },
]

for anuncio_data in anuncios_data:
    anuncio, created = Anuncio.objects.get_or_create(
        nome=anuncio_data['nome'],
        defaults=anuncio_data
    )
    status = 'Criado' if created else 'Já existe'
    print(f"  Anúncio: {anuncio.nome} - {status}")

print("\nDados de demonstração carregados com sucesso!")
