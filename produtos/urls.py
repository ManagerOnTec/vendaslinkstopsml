from django.urls import path
from .views import (
    ProdutoListView, CategoriaListView,
    ProdutoAutomaticoListView, AtualizarProdutosAPIView
)

app_name = 'produtos'

urlpatterns = [
    path('', ProdutoAutomaticoListView.as_view(), name='lista_automatica'),
    path('curadoria/', ProdutoListView.as_view(), name='lista'),
    path('categoria/<slug:slug>/', CategoriaListView.as_view(), name='categoria'),
    # Endpoint para Cloud Scheduler / cron
    path('api/atualizar-produtos/', AtualizarProdutosAPIView.as_view(), name='api_atualizar'),
]
