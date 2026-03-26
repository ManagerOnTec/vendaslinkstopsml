from django.urls import path
from .views import (
    ProdutosCombinedListView, CategoriaListView,
    AtualizarProdutosAPIView, NewsletterSignupAPIView, 
    pagina_legal, ads_txt
)

app_name = 'produtos'

urlpatterns = [
    # Página principal: lista todos os produtos (manuais + automáticos)
    path('', ProdutosCombinedListView.as_view(), name='lista'),
    # Página de categoria: lista produtos de uma categoria (manuais + automáticos)
    path('categoria/<slug:slug>/', CategoriaListView.as_view(), name='categoria'),
    # Endpoint para Cloud Scheduler / cron
    path('api/atualizar-produtos/', AtualizarProdutosAPIView.as_view(), name='api_atualizar'),
    # Endpoint para newsletter signup
    path('api/newsletter/signup/', NewsletterSignupAPIView.as_view(), name='api_newsletter_signup'),
    # Páginas legais
    path('legal/<str:tipo>/', pagina_legal, name='pagina_legal'),
    # Google AdSense verification
    path('ads.txt', ads_txt, name='ads_txt'),
]

