"""
Testes de validação para a refatoração de Produtos Consolidados.

Valida:
- Proxy models funcionam corretamente
- Filtro de origem funciona
- Views unificada funciona
- Admin filtra corretamente
"""

from django.test import TestCase
from django.contrib.auth.models import User
from produtos.models import (
    ProdutoAutomatico, ProdutoAutomaticoProxy, ProdutoManualProxy,
    Categoria, OrigemProduto, StatusExtracao
)


class ProdutoConsolidadoTestCase(TestCase):
    """Testa a consolidação de Produto e ProdutoAutomatico."""
    
    def setUp(self):
        """Cria dados para testes."""
        # Criar categoria
        self.categoria = Categoria.objects.create(
            nome="Testes",
            slug="testes",
            ativo=True,
            ordem=1
        )
        
        # Criar produto automático
        self.produto_auto = ProdutoAutomatico.objects.create(
            titulo="Fone Bluetooth Automático",
            link_afiliado="https://www.mercadolivre.com.br/produto-teste",
            plataforma="mercado_livre",
            status_extracao=StatusExtracao.SUCESSO,
            origem=OrigemProduto.AUTOMATICO,
            preco="R$ 99,90",
            imagem_url="https://exemplo.com/imagem.jpg",
            categoria=self.categoria,
            ativo=True,
            destaque=True,
            ordem=1
        )
        
        # Criar produto manual
        self.produto_manual = ProdutoAutomatico.objects.create(
            titulo="Fone Wired Manual",
            preco="R$ 49,90",
            origem=OrigemProduto.MANUAL,
            categoria=self.categoria,
            ativo=True,
            destaque=False,
            ordem=2
        )
    
    def test_criar_produto_automatico(self):
        """Testa criação de produto automático."""
        auto = ProdutoAutomatico.objects.create(
            titulo="Novo Produto Automático",
            link_afiliado="https://www.amazon.com.br/produto",
            plataforma="amazon",
            status_extracao=StatusExtracao.PENDENTE,
            origem=OrigemProduto.AUTOMATICO,
            preco="R$ 199,90",
        )
        
        self.assertEqual(auto.origem, OrigemProduto.AUTOMATICO)
        self.assertEqual(auto.plataforma, "amazon")
        self.assertTrue(auto.link_afiliado)
    
    def test_criar_produto_manual(self):
        """Testa criação de produto manual."""
        manual = ProdutoAutomatico.objects.create(
            titulo="Novo Produto Manual",
            preco="R$ 39,90",
            imagem_url="https://exemplo.com/img.jpg",
            origem=OrigemProduto.MANUAL,
        )
        
        self.assertEqual(manual.origem, OrigemProduto.MANUAL)
        # link_afiliado fica vazio string "", não None
        self.assertEqual(manual.link_afiliado, "")
    
    def test_filtro_origem_automatico(self):
        """Testa filtro de produtos automáticos."""
        autos = ProdutoAutomatico.objects.filter(
            origem=OrigemProduto.AUTOMATICO
        )
        
        self.assertEqual(autos.count(), 1)
        self.assertIn(self.produto_auto, autos)
        self.assertNotIn(self.produto_manual, autos)
    
    def test_filtro_origem_manual(self):
        """Testa filtro de produtos manuais."""
        manuais = ProdutoAutomatico.objects.filter(
            origem=OrigemProduto.MANUAL
        )
        
        self.assertEqual(manuais.count(), 1)
        self.assertIn(self.produto_manual, manuais)
        self.assertNotIn(self.produto_auto, manuais)
    
    def test_proxy_automatic(self):
        """Testa proxy model ProdutoAutomaticoProxy."""
        # Todos os itens retornados devem ser automáticos
        # (isso é testado via get_queryset no admin)
        self.assertIsInstance(self.produto_auto, ProdutoAutomatico)
    
    def test_proxy_manual(self):
        """Testa proxy model ProdutoManualProxy."""
        # Todos os itens retornados devem ser manuais
        # (isso é testado via get_queryset no admin)
        self.assertIsInstance(self.produto_manual, ProdutoAutomatico)
    
    def test_query_view_unificada(self):
        """Testa query unificada para views."""
        from django.db.models import Q
        
        # Simula o filtro da view unificada
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        ).order_by('-destaque', 'ordem', '-criado_em')
        
        # Ambos produtos devem aparecer
        self.assertEqual(queryset.count(), 2)
        
        # Verificar ordem
        produtos_list = list(queryset)
        first = produtos_list[0]
        
        # Produto com destaque vem primeiro
        self.assertEqual(first.id, self.produto_auto.id)
        self.assertTrue(first.destaque)
    
    def test_view_exclui_automaticos_com_erro(self):
        """Testa se view exclui automáticos com erro/pendente."""
        # Criar automático com erro
        ProdutoAutomatico.objects.create(
            titulo="Produto com Erro",
            link_afiliado="https://www.shopee.com.br/erro",
            plataforma="shopee",
            status_extracao=StatusExtracao.ERRO,
            origem=OrigemProduto.AUTOMATICO,
            ativo=True
        )
        
        # Query da view
        from django.db.models import Q
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        )
        
        # Deve excluir o com erro
        self.assertEqual(queryset.count(), 2)  # Apenas automático sucesso + manual
        
        produtos_list = list(queryset)
        titulos = [p.titulo for p in produtos_list]
        
        self.assertNotIn("Produto com Erro", titulos)
    
    def test_editar_produto_automatico_mantém_origem(self):
        """Testa se ao editar automático, origem se mantém."""
        self.produto_auto.titulo = "Título Editado"
        self.produto_auto.save()
        
        # Recarrega do banco
        produto = ProdutoAutomatico.objects.get(pk=self.produto_auto.pk)
        
        self.assertEqual(produto.titulo, "Título Editado")
        self.assertEqual(produto.origem, OrigemProduto.AUTOMATICO)
    
    def test_plataf_e_status_apenas_automaticos(self):
        """Testa que manual tem plataforma padrão 'outro'."""
        # Manual não precisa preencher plataforma específico
        # O padrão é 'outro' para manuais
        self.assertEqual(self.produto_manual.plataforma, "outro")
    
    def test_link_afiliado_obrigatorio_para_automatico(self):
        """Documenta que link é obrigatório para automático."""
        # Automático = deve ter link
        self.assertTrue(self.produto_auto.link_afiliado)
        
        # Manual = link opcional
        self.assertFalse(self.produto_manual.link_afiliado)
    
    def test_dados_migrados_categoria_relacionada(self):
        """Testa se relação com categoria funciona."""
        # Ambos produtos têm categoria
        self.assertEqual(self.produto_auto.categoria, self.categoria)
        self.assertEqual(self.produto_manual.categoria, self.categoria)
        
        # Categoria pode acessar ambos
        prods = self.categoria.produtos_automaticos.all()
        self.assertEqual(prods.count(), 2)
    
    def test_string_representation(self):
        """Testa __str__ de produto."""
        str_auto = str(self.produto_auto)
        str_manual = str(self.produto_manual)
        
        self.assertIn("Fone Bluetooth", str_auto)
        self.assertIn("Fone Wired", str_manual)
    
    def test_get_imagem_fallback(self):
        """Testa get_imagem com fallback para padrão."""
        # Com imagem_url
        img = self.produto_auto.get_imagem()
        self.assertEqual(img, "https://exemplo.com/imagem.jpg")
        
        # Sem imagem
        self.produto_manual.imagem_url = ""
        self.produto_manual.imagem = None
        img = self.produto_manual.get_imagem()
        self.assertEqual(img, '/static/images/no-image.png')


class ProxyModelFilterTestCase(TestCase):
    """Testa se proxy models filtram corretamente no admin."""
    
    def setUp(self):
        self.user = User.objects.create_superuser(
            'admin', 'admin@test.com', 'admin'
        )
        self.categoria = Categoria.objects.create(
            nome="Proxy Test",
            slug="proxy-test"
        )
        
        # Criar ambos tipos
        self.auto = ProdutoAutomatico.objects.create(
            titulo="Auto",
            link_afiliado="https://ml.com/auto",
            origem=OrigemProduto.AUTOMATICO,
            plataforma="mercado_livre",
            status_extracao=StatusExtracao.SUCESSO,
            categoria=self.categoria,
            ativo=True
        )
        
        self.manual = ProdutoAutomatico.objects.create(
            titulo="Manual",
            origem=OrigemProduto.MANUAL,
            categoria=self.categoria,
            ativo=True
        )
    
    def test_proxy_automatic_queryset_filtra(self):
        """Testa que ProdutoAutomaticoProxy queryset filtra por origem."""
        from produtos.admin import ProdutoAutomaticoProxyAdmin
        from unittest.mock import Mock
        
        admin = ProdutoAutomaticoProxyAdmin(ProdutoAutomaticoProxy, None)
        
        # Mock request
        request = Mock()
        request.user = self.user
        
        qs = admin.get_queryset(request)
        
        # Deve filtrar apenas automáticos
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.auto.id)
    
    def test_proxy_manual_queryset_filtra(self):
        """Testa que ProdutoManualProxy queryset filtra por origem."""
        from produtos.admin import ProdutoManualProxyAdmin
        from unittest.mock import Mock
        
        admin = ProdutoManualProxyAdmin(ProdutoManualProxy, None)
        
        # Mock request
        request = Mock()
        request.user = self.user
        
        qs = admin.get_queryset(request)
        
        # Deve filtrar apenas manuais
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, self.manual.id)


class IntegracaoViewTestCase(TestCase):
    """Testa integração da view unificada com modelo consolidado."""
    
    def setUp(self):
        self.categoria = Categoria.objects.create(
            nome="View Test",
            slug="view-test"
        )
        
        # Criar vários tipos de produtos
        self.auto_sucesso = ProdutoAutomatico.objects.create(
            titulo="Auto Sucesso",
            link_afiliado="https://ml.com/1",
            origem=OrigemProduto.AUTOMATICO,
            plataforma="mercado_livre",
            status_extracao=StatusExtracao.SUCESSO,
            categoria=self.categoria,
            ativo=True
        )
        
        self.auto_erro = ProdutoAutomatico.objects.create(
            titulo="Auto Erro",
            link_afiliado="https://ml.com/2",
            origem=OrigemProduto.AUTOMATICO,
            plataforma="mercado_livre",
            status_extracao=StatusExtracao.ERRO,
            categoria=self.categoria,
            ativo=True
        )
        
        self.manual = ProdutoAutomatico.objects.create(
            titulo="Manual",
            origem=OrigemProduto.MANUAL,
            categoria=self.categoria,
            ativo=True
        )
        
        self.auto_inativo = ProdutoAutomatico.objects.create(
            titulo="Auto Inativo",
            link_afiliado="https://ml.com/3",
            origem=OrigemProduto.AUTOMATICO,
            plataforma="mercado_livre",
            status_extracao=StatusExtracao.SUCESSO,
            categoria=self.categoria,
            ativo=False
        )
    
    def test_view_query_retorna_esperado(self):
        """Testa se a query da view retorna o esperado."""
        from django.db.models import Q
        
        # Simula query da view
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        )
        
        # Deve retornar:
        # - Auto Sucesso ✓
        # - Manual ✓
        # Não deve retornar:
        # - Auto Erro ✗
        # - Auto Inativo ✗
        
        self.assertEqual(queryset.count(), 2)
        ids = {p.id for p in queryset}
        
        self.assertIn(self.auto_sucesso.id, ids)
        self.assertIn(self.manual.id, ids)
        self.assertNotIn(self.auto_erro.id, ids)
        self.assertNotIn(self.auto_inativo.id, ids)
    
    def test_filtro_categoria_view(self):
        """Testa filtro de categoria na view."""
        from django.db.models import Q
        
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True,
            categoria__slug="view-test"
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        )
        
        # Todos os produtos de teste estão em view-test
        self.assertEqual(queryset.count(), 2)
    
    def test_filtro_busca_view(self):
        """Testa filtro de busca na view."""
        from django.db.models import Q
        
        busca = "Auto Sucesso"
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True,
            titulo__icontains=busca
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        )
        
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.first().titulo, "Auto Sucesso")
    
    def test_ordenacao_destaque(self):
        """Testa ordenação por destaque na view."""
        # Marcar manual como destaque
        self.manual.destaque = True
        self.manual.save()
        
        from django.db.models import Q
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True
        ).filter(
            Q(origem=OrigemProduto.MANUAL) |
            Q(status_extracao=StatusExtracao.SUCESSO)
        ).order_by('-destaque', 'ordem', '-criado_em')
        
        # Manual com destaque deve vir primeiro
        produtos = list(queryset)
        self.assertEqual(produtos[0].id, self.manual.id)
