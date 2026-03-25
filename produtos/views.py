import time
import logging
from typing import Tuple, List
from itertools import chain

from django.views.generic import ListView
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, QuerySet
from django.core.paginator import Paginator

from .models import (
    ProdutoAutomatico, Categoria, Anuncio,
    AgendamentoAtualizacao, LogAtualizacao, DiaSemana, DocumentoLegal
)

logger = logging.getLogger(__name__)


class ProdutosCombinedListView(ListView):
    """
    View unificada que lista produtos (modelo único: ProdutoAutomatico com proxy models).
    
    Características:
    - Filtra ativos
    - Suporta busca por título (query 'q')
    - Suporta filtro por categoria
    - Mostra ambos manuais e automáticos na mesma listview
    
    Ordenação: destaque > ordem > data criação
    """
    template_name = 'produtos/lista.html'
    context_object_name = 'produtos'
    paginate_by = settings.PRODUTOS_POR_PAGINA
    
    def get_queryset(self) -> List:
        """
        Retorna lista UNIFICADA de produtos (modelo único ProdutoAutomatico).
        
        FILTROS APLICADOS:
        - Apenas produtos ATIVOS (ativo=True)
        - Apenas produtos com status_extracao='sucesso' OU origem='manual'
        - Suporta busca por título
        - Suporta filtro por categoria
        """
        busca = self.request.GET.get('q', '').strip()
        categoria_slug = self.request.GET.get('categoria', '').strip()
        
        # Query base: produtos ativos
        queryset = ProdutoAutomatico.objects.filter(ativo=True).select_related('categoria')
        
        # Filtro de categoria (se fornecido)
        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)
        
        # Filtro de busca (se fornecido)
        if busca:
            queryset = queryset.filter(titulo__icontains=busca)
        
        # Produtos automáticos devem ter status='sucesso'
        # Produtos manuais não têm restrição de status (são sempre sucesso)
        from .models import OrigemProduto
        queryset = queryset.filter(
            Q(origem=OrigemProduto.MANUAL) |  # Manuais: sem restrição
            Q(status_extracao='sucesso')       # Automáticos: apenas sucesso
        )
        
        # Ordenar: destaque > ordem > data criação (decrescente)
        queryset = queryset.order_by('-destaque', 'ordem', '-criado_em')
        
        count_manuais = queryset.filter(origem=OrigemProduto.MANUAL).count()
        count_auto = queryset.filter(origem=OrigemProduto.AUTOMATICO).count()
        
        logger.info(
            f"🔍 Listando {count_manuais} manuais + "
            f"{count_auto} automáticos = {queryset.count()} total"
        )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(ativo=True).order_by('ordem', 'nome')
        context['categoria_atual'] = self.request.GET.get('categoria', '')
        context['busca_atual'] = self.request.GET.get('q', '')
        
        anuncios = Anuncio.objects.filter(ativo=True)
        context['anuncios_topo'] = anuncios.filter(posicao='topo')
        context['anuncios_meio'] = anuncios.filter(posicao='meio')
        context['anuncios_rodape'] = anuncios.filter(posicao='rodape')
        context['anuncios_lateral'] = anuncios.filter(posicao='lateral')
        context['anuncio_intervalo'] = settings.ANUNCIO_A_CADA_N_PRODUTOS
        
        return context
    
    def paginate_queryset(self, queryset, page_size):
        """Override para lidar com lista em vez de QuerySet."""
        paginator = Paginator(queryset, page_size)
        page_number = self.request.GET.get(self.page_kwarg, 1)
        page_obj = paginator.get_page(page_number)
        return paginator, page_obj, page_obj.object_list, page_obj.has_other_pages()


class CategoriaListView(ProdutosCombinedListView):
    """
    View para listar produtos de uma categoria específica.
    Herda da ProdutosCombinedListView, apenas força o filtro de categoria via URL.
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Categoria vem da URL, não de GET
        categoria_slug = self.kwargs.get('slug', '')
        context['categoria_atual'] = categoria_slug
        return context
    
    def get_queryset(self) -> QuerySet:
        """
        Retorna produtos filtrando pela categoria da URL.
        Usa a mesma lógica unificada de ProdutosCombinedListView, apenas força a categoria.
        """
        categoria_slug = self.kwargs.get('slug', '').strip()
        
        # Query base: produtos ativos
        queryset = ProdutoAutomatico.objects.filter(ativo=True).select_related('categoria')
        
        # Filtro de categoria (obrigatório nesta view)
        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)
        
        # Suporta busca por título
        busca = self.request.GET.get('q', '').strip()
        if busca:
            queryset = queryset.filter(titulo__icontains=busca)
        
        # Produtos automáticos devem ter status='sucesso'
        # Produtos manuais não têm restrição de status
        from .models import OrigemProduto
        queryset = queryset.filter(
            Q(origem=OrigemProduto.MANUAL) |  # Manuais: sem restrição
            Q(status_extracao='sucesso')       # Automáticos: apenas sucesso
        )
        
        # Ordenar: destaque > ordem > data criação (decrescente)
        queryset = queryset.order_by('-destaque', 'ordem', '-criado_em')
        
        logger.info(
            f"📁 Categoria '{categoria_slug}': {queryset.count()} produtos"
        )
        
        return queryset


@method_decorator(csrf_exempt, name='dispatch')
class AtualizarProdutosAPIView(View):
    """Endpoint para Cloud Scheduler ou cron chamar a atualização.

    GET /api/atualizar-produtos/
        Verifica agendamentos ativos para o horário atual.

    POST /api/atualizar-produtos/
        Força a atualização de todos os produtos ativos.

    Header de segurança: X-Cron-Secret (configurar em .env)
    """

    def _verificar_auth(self, request):
        """Verifica autenticação via header ou settings."""
        cron_secret = getattr(settings, 'CRON_SECRET', '')
        if cron_secret:
            header_secret = request.headers.get('X-Cron-Secret', '')
            if header_secret != cron_secret:
                return False
        return True

    def get(self, request):
        if not self._verificar_auth(request):
            return JsonResponse({'error': 'Não autorizado'}, status=403)

        from django.utils import timezone
        from datetime import datetime, timedelta

        agora = timezone.localtime()
        hora_atual = agora.time()
        dia_semana_atual = agora.weekday()

        dia_map = {
            0: DiaSemana.SEG, 1: DiaSemana.TER, 2: DiaSemana.QUA,
            3: DiaSemana.QUI, 4: DiaSemana.SEX, 5: DiaSemana.SAB,
            6: DiaSemana.DOM,
        }
        dia_atual_choice = dia_map.get(dia_semana_atual)
        eh_dia_util = dia_semana_atual < 5

        agendamentos = AgendamentoAtualizacao.objects.filter(ativo=True)
        resultados = []

        for ag in agendamentos:
            ag_hora = ag.horario
            hora_min = (
                datetime.combine(agora.date(), ag_hora)
                - timedelta(minutes=30)
            ).time()
            hora_max = (
                datetime.combine(agora.date(), ag_hora)
                + timedelta(minutes=30)
            ).time()

            dentro_horario = hora_min <= hora_atual <= hora_max

            dia_ok = False
            if ag.dias_semana == DiaSemana.TODOS:
                dia_ok = True
            elif ag.dias_semana == DiaSemana.SEG_SEX:
                dia_ok = eh_dia_util
            elif ag.dias_semana == dia_atual_choice:
                dia_ok = True

            if dentro_horario and dia_ok:
                ultimo_log = LogAtualizacao.objects.filter(
                    agendamento=ag,
                    executado_em__gte=agora - timedelta(hours=1)
                ).first()

                if ultimo_log:
                    resultados.append({
                        'agendamento': ag.nome,
                        'status': 'já executado recentemente',
                    })
                    continue

                resultado = self._executar(ag)
                resultados.append(resultado)

        if not resultados:
            return JsonResponse({
                'status': 'nenhum agendamento para executar',
                'hora_atual': hora_atual.strftime('%H:%M'),
            })

        return JsonResponse({'resultados': resultados})

    def post(self, request):
        if not self._verificar_auth(request):
            return JsonResponse({'error': 'Não autorizado'}, status=403)

        resultado = self._executar(agendamento=None)
        return JsonResponse(resultado)

    def _executar(self, agendamento=None):
        from .scraper import processar_produto_automatico

        inicio = time.time()
        produtos = ProdutoAutomatico.objects.filter(ativo=True)
        if agendamento and agendamento.atualizar_apenas_ativos:
            produtos = produtos.filter(ativo=True)

        total = produtos.count()
        sucesso = 0
        erros = 0
        detalhes_list = []

        for produto in produtos:
            try:
                result = processar_produto_automatico(produto)
                if result:
                    sucesso += 1
                    detalhes_list.append(
                        f'OK: {produto.titulo[:60]} -> {produto.preco}'
                    )
                else:
                    erros += 1
                    detalhes_list.append(
                        f'ERRO: {produto.titulo[:60]} -> '
                        f'{produto.erro_extracao[:80]}'
                    )
            except Exception as e:
                erros += 1
                detalhes_list.append(
                    f'EXCE\u00c7\u00c3O: {produto.id} -> {str(e)[:80]}'
                )

        duracao = time.time() - inicio

        LogAtualizacao.objects.create(
            agendamento=agendamento,
            total_produtos=total,
            sucesso=sucesso,
            erros=erros,
            detalhes='\n'.join(detalhes_list),
            duracao_segundos=round(duracao, 2)
        )

        return {
            'agendamento': agendamento.nome if agendamento else 'Forçado',
            'total': total,
            'sucesso': sucesso,
            'erros': erros,
            'duracao_segundos': round(duracao, 2),
        }


def pagina_legal(request, tipo):
    """Renderiza página de documentos legais (Privacidade, Termos, Afiliados)."""
    from django.shortcuts import render, get_object_or_404
    
    documento = get_object_or_404(DocumentoLegal, tipo=tipo)
    return render(request, 'legal.html', {'documento': documento})


def ads_txt(request):
    """Retorna arquivo ads.txt para verificação do Google AdSense."""
    from django.http import HttpResponse
    
    pub_id = getattr(settings, 'GOOGLE_ADSENSE_ID', '')
    if not pub_id:
        # ID padrão se não configurado
        pub_id = 'pub-4703772286442200'
    
    conteudo = f"google.com, {pub_id}, DIRECT, f08c47fec0942fa0"
    return HttpResponse(conteudo, content_type="text/plain")
