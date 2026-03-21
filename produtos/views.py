import time
import logging

from django.views.generic import ListView
from django.views import View
from django.http import JsonResponse
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Produto, ProdutoAutomatico, Categoria, Anuncio,
    AgendamentoAtualizacao, LogAtualizacao, DiaSemana
)

logger = logging.getLogger(__name__)


class ProdutoListView(ListView):
    """View principal: lista todos os produtos manuais ativos."""
    model = Produto
    template_name = 'produtos/lista.html'
    context_object_name = 'produtos'
    paginate_by = settings.PRODUTOS_POR_PAGINA

    def get_queryset(self):
        queryset = Produto.objects.filter(ativo=True).select_related('categoria')
        categoria_slug = self.request.GET.get('categoria')
        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)
        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(titulo__icontains=busca)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(ativo=True)
        context['categoria_atual'] = self.request.GET.get('categoria', '')
        context['busca_atual'] = self.request.GET.get('q', '')
        context['pagina_tipo'] = 'manual'
        anuncios = Anuncio.objects.filter(ativo=True)
        context['anuncios_topo'] = anuncios.filter(posicao='topo')
        context['anuncios_meio'] = anuncios.filter(posicao='meio')
        context['anuncios_rodape'] = anuncios.filter(posicao='rodape')
        context['anuncios_lateral'] = anuncios.filter(posicao='lateral')
        context['anuncio_intervalo'] = settings.ANUNCIO_A_CADA_N_PRODUTOS
        return context


class CategoriaListView(ListView):
    """View para listar produtos de uma categoria específica."""
    model = Produto
    template_name = 'produtos/lista.html'
    context_object_name = 'produtos'
    paginate_by = settings.PRODUTOS_POR_PAGINA

    def get_queryset(self):
        return Produto.objects.filter(
            ativo=True,
            categoria__slug=self.kwargs.get('slug')
        ).select_related('categoria')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(ativo=True)
        context['categoria_atual'] = self.kwargs.get('slug', '')
        context['busca_atual'] = ''
        context['pagina_tipo'] = 'manual'
        anuncios = Anuncio.objects.filter(ativo=True)
        context['anuncios_topo'] = anuncios.filter(posicao='topo')
        context['anuncios_meio'] = anuncios.filter(posicao='meio')
        context['anuncios_rodape'] = anuncios.filter(posicao='rodape')
        context['anuncios_lateral'] = anuncios.filter(posicao='lateral')
        context['anuncio_intervalo'] = settings.ANUNCIO_A_CADA_N_PRODUTOS
        return context


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


class ProdutoAutomaticoListView(ListView):
    """View da segunda index: lista produtos com dados extraídos automaticamente do ML."""
    model = ProdutoAutomatico
    template_name = 'produtos/lista_automatica.html'
    context_object_name = 'produtos'
    paginate_by = settings.PRODUTOS_POR_PAGINA

    def get_queryset(self):
        queryset = ProdutoAutomatico.objects.filter(
            ativo=True,
            status_extracao='sucesso'
        ).select_related('categoria')
        categoria_slug = self.request.GET.get('categoria')
        if categoria_slug:
            queryset = queryset.filter(categoria__slug=categoria_slug)
        busca = self.request.GET.get('q')
        if busca:
            queryset = queryset.filter(titulo__icontains=busca)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.filter(ativo=True)
        context['categoria_atual'] = self.request.GET.get('categoria', '')
        context['busca_atual'] = self.request.GET.get('q', '')
        context['pagina_tipo'] = 'automatico'
        anuncios = Anuncio.objects.filter(ativo=True)
        context['anuncios_topo'] = anuncios.filter(posicao='topo')
        context['anuncios_meio'] = anuncios.filter(posicao='meio')
        context['anuncios_rodape'] = anuncios.filter(posicao='rodape')
        context['anuncios_lateral'] = anuncios.filter(posicao='lateral')
        context['anuncio_intervalo'] = settings.ANUNCIO_A_CADA_N_PRODUTOS
        return context
