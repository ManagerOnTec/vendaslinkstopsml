"""
Testes para a refatoração de unificação de produtos.
Execute com: python manage.py test produtos.tests
"""
from django.test import TestCase, Client
from django.urls import reverse
from datetime import datetime
from produtos.models import Produto, ProdutoAutomatico, Categoria


class TestProdutosCombinedListView(TestCase):
    """Testa a nova view unificada de produtos."""
    
    def setUp(self):
        """Setup: criar dados de teste."""
        self.client = Client()
        
        # Criar categoria
        self.categoria = Categoria.objects.create(
            nome='Eletrônicos',
            slug='eletronicos',
            ativo=True,
            ordem=1
        )
        
        # Criar produtos manuais
        self.produto_manual_1 = Produto.objects.create(
            titulo='Fone Manual 1',
            link_afiliado='https://mercado.livre.com/produto1',
            preco='R$ 100,00',
            categoria=self.categoria,
            destaque=True,
            ativo=True,
            ordem=1
        )
        
        self.produto_manual_2 = Produto.objects.create(
            titulo='Fone Manual 2',
            link_afiliado='https://mercado.livre.com/produto2',
            preco='R$ 200,00',
            categoria=self.categoria,
            destaque=False,
            ativo=True,
            ordem=2
        )
        
        # Criar produtos automáticos
        self.produto_auto_1 = ProdutoAutomatico.objects.create(
            link_afiliado='https://mercado.livre.com/auto1',
            titulo='Fone Automático 1',
            imagem_url='https://example.com/img1.jpg',
            preco='R$ 150,00',
            categoria=self.categoria,
            status_extracao='sucesso',
            destaque=False,
            ativo=True,
            ordem=3
        )
        
        self.produto_auto_2 = ProdutoAutomatico.objects.create(
            link_afiliado='https://mercado.livre.com/auto2',
            titulo='Fone Automático 2',
            imagem_url='https://example.com/img2.jpg',
            preco='R$ 250,00',
            categoria=self.categoria,
            status_extracao='sucesso',
            destaque=True,
            ativo=True,
            ordem=4
        )
        
        # Produto automático com status falho (não deve aparecer)
        self.produto_auto_failed = ProdutoAutomatico.objects.create(
            link_afiliado='https://mercado.livre.com/auto_failed',
            titulo='Fone Automático Falhou',
            status_extracao='erro',
            ativo=True,
        )
    
    def test_pagina_principal_combina_produtos(self):
        """Testa se a página principal lista produtos manuais + automáticos."""
        response = self.client.get(reverse('produtos:lista'))
        
        self.assertEqual(response.status_code, 200)
        produtos = response.context['produtos']
        
        # Deve ter 4 produtos (2 manuais + 2 automáticos com sucesso)
        self.assertEqual(len(produtos), 4)
        
        # Verificar que os produtos são os corretos
        titulos = [p.titulo for p in produtos]
        self.assertIn('Fone Manual 1', titulos)
        self.assertIn('Fone Manual 2', titulos)
        self.assertIn('Fone Automático 1', titulos)
        self.assertIn('Fone Automático 2', titulos)
        
        # Produto falho não deve aparecer
        self.assertNotIn('Fone Automático Falhou', titulos)
    
    def test_filtro_por_categoria(self):
        """Testa filtro de categoria."""
        response = self.client.get(
            reverse('produtos:categoria', args=[self.categoria.slug])
        )
        
        self.assertEqual(response.status_code, 200)
        produtos = response.context['produtos']
        
        # Todos são da categoria Eletrônicos
        self.assertEqual(len(produtos), 4)
        for p in produtos:
            self.assertEqual(p.categoria.slug, self.categoria.slug)
    
    def test_filtro_por_busca(self):
        """Testa filtro de busca por título."""
        response = self.client.get(
            reverse('produtos:lista') + '?q=Automático'
        )
        
        self.assertEqual(response.status_code, 200)
        produtos = response.context['produtos']
        
        # Deve ter apenas os 2 automáticos
        self.assertEqual(len(produtos), 2)
        for p in produtos:
            self.assertIn('Automático', p.titulo)
    
    def test_filtro_categoria_e_busca_combinados(self):
        """Testa filtros de categoria e busca combinados."""
        response = self.client.get(
            reverse('produtos:categoria', args=[self.categoria.slug]) + '?q=Manual'
        )
        
        self.assertEqual(response.status_code, 200)
        produtos = response.context['produtos']
        
        # Deve ter apenas os 2 manuais da categoria
        self.assertEqual(len(produtos), 2)
        for p in produtos:
            self.assertIn('Manual', p.titulo)
            self.assertEqual(p.categoria.slug, self.categoria.slug)
    
    def test_template_renderiza_corretamente(self):
        """Testa se o template renderiza sem erros."""
        response = self.client.get(reverse('produtos:lista'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'produtos/lista.html')
        
        # Verificar elementos esperados no template
        self.assertContains(response, 'Ofertas em Destaque')
        self.assertContains(response, 'Eletrônicos')  # Categoria
    
    def test_contexto_categorias(self):
        """Testa se as categorias estão no contexto."""
        response = self.client.get(reverse('produtos:lista'))
        
        categorias = response.context['categorias']
        self.assertEqual(categorias.count(), 1)
        self.assertEqual(categorias.first().nome, 'Eletrônicos')


class TestAdminFallback(TestCase):
    """Testa se o admin de Produto manual ainda funciona como fallback."""
    
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nome='Teste',
            slug='teste'
        )
    
    def test_produto_manual_pode_ser_criado(self):
        """Testa se produtos manuais ainda podem ser criados no admin."""
        produto = Produto.objects.create(
            titulo='Produto Manual Fallback',
            link_afiliado='https://mercado.livre.com/fallback',
            preco='R$ 199,99',
            categoria=self.categoria,
            ativo=True
        )
        
        self.assertIsNotNone(produto.id)
        self.assertEqual(produto.titulo, 'Produto Manual Fallback')
    
    def test_produto_manual_aparece_na_listagem(self):
        """Testa se produtos manuais aparecem na listagem combinada."""
        produto = Produto.objects.create(
            titulo='Produto Manual para Listagem',
            link_afiliado='https://mercado.livre.com/manual',
            preco='R$ 299,99',
            categoria=self.categoria,
            ativo=True
        )
        
        response = Client().get(reverse('produtos:lista'))
        produtos = response.context['produtos']
        
        titulos = [p.titulo for p in produtos]
        self.assertIn('Produto Manual para Listagem', titulos)

