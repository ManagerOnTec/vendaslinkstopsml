from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
import logging
from .models import (
    Categoria, Anuncio, ProdutoAutomatico, 
    ProdutoAutomaticoProxy, ProdutoManualProxy,
    AgendamentoAtualizacao, LogAtualizacao, DocumentoLegal, EscalonamentoConfig,
    Cliente, SiteMaintenanceConfig, PlataformaEcommerce
)

logger = logging.getLogger(__name__)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'ativo', 'ordem', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    list_editable = ('ativo', 'ordem')
    prepopulated_fields = {'slug': ('nome',)}
    ordering = ('ordem', 'nome')


@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'posicao', 'ativo', 'ordem', 'criado_em')
    list_filter = ('posicao', 'ativo')
    search_fields = ('nome',)
    list_editable = ('ativo', 'ordem')
    ordering = ('posicao', 'ordem')

    fieldsets = (
        ('Identificação', {
            'fields': ('nome', 'posicao')
        }),
        ('Código do Anúncio', {
            'fields': ('codigo_html',),
            'description': 'Cole o código HTML/JavaScript do Google AdSense ou outro provedor de anúncios.'
        }),
        ('Configuração', {
            'fields': ('ativo', 'ordem')
        }),
    )


@admin.register(PlataformaEcommerce)
class PlataformaEcommerceAdmin(admin.ModelAdmin):
    """Admin para gerenciar plataformas de e-commerce disponíveis."""
    list_display = ('nome', 'chave', 'ativo', 'ordem', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('nome', 'chave')
    list_editable = ('ativo', 'ordem')
    ordering = ('ordem', 'nome')
    readonly_fields = ('criado_em',)
    
    fieldsets = (
        ('Identificação', {
            'fields': ('chave', 'nome')
        }),
        ('Configuração', {
            'fields': ('ativo', 'ordem')
        }),
        ('Metadata', {
            'fields': ('criado_em',),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProdutoAutomaticoProxy)
class ProdutoAutomaticoProxyAdmin(admin.ModelAdmin):
    """Interface para criar/atualizar produtos via extração automática de link.
    
    - Links são obrigatórios
    - Título, imagem, preço são readonly (extraídos automaticamente)
    - Sistema executa extração ao salvar
    """
    list_display = (
        'titulo_display', 'plataforma_badge', 'preview_imagem', 'categoria_display', 'preco', 'status_badge',
        'falhas_consecutivas', 'destaque', 'ativo', 'ordem', 'criado_em'
    )
    list_filter = ('plataforma', 'status_extracao', 'ativo', 'destaque', 'categoria', 'falhas_consecutivas')
    search_fields = ('titulo', 'link_afiliado')
    list_editable = ('destaque', 'ativo', 'ordem')
    list_per_page = 25
    ordering = ('-destaque', 'ordem', '-criado_em')
    readonly_fields = (
        'origem', 'plataforma', 'titulo', 'imagem_url', 'preco', 'preco_original', 'descricao',
        'url_final', 'status_extracao', 'erro_extracao',
        'preview_imagem_grande', 'criado_em', 'atualizado_em', 'ultima_extracao',
        'falhas_consecutivas', 'motivo_desativacao'
    )
    actions = ['extrair_dados_action', 'reextrair_dados_action', 'resetar_falhas_action', 'importar_produtos_arquivo_action']

    fieldsets = (
        ('Link do Produto (COLE AQUI)', {
            'fields': ('link_afiliado', 'plataforma', 'origem'),
            'description': (
                '<strong style="font-size:14px;color:#1a73e8;">'
                'Cole o link do produto (Mercado Livre, Amazon, Shopee, Shein). '
                'Os dados serão extraídos automaticamente! A plataforma é detectada pelo sistema.</strong>'
            )
        }),
        ('Dados Extraídos Automaticamente', {
            'fields': (
                'titulo', 'preview_imagem_grande', 'imagem_url',
                'preco', 'preco_original', 'descricao', 'url_final'
            ),
            'classes': ('collapse',),
            'description': 'Estes campos são preenchidos automaticamente pelo scraper. Para editar, veja a seção "Configuração Manual".'
        }),
        ('Configuração Manual', {
            'fields': ('categoria', 'destaque', 'ativo', 'ordem'),
            'description': 'Categoria é extraída automaticamente mas pode ser alterada aqui se necessário.'
        }),
        ('Status da Extração', {
            'fields': ('status_extracao', 'erro_extracao', 'ultima_extracao'),
            'classes': ('collapse',)
        }),
        ('Monitoramento de Falhas', {
            'fields': ('falhas_consecutivas', 'motivo_desativacao'),
            'description': 'Produto é desativado automaticamente após falhas consecutivas'
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Filtrar apenas produtos de origem AUTOMÁTICA para esta interface."""
        from .models import OrigemProduto
        qs = super().get_queryset(request)
        return qs.filter(origem=OrigemProduto.AUTOMATICO)

    def titulo_display(self, obj):
        titulo = obj.titulo or '(Aguardando extração...)'
        if len(titulo) > 60:
            titulo = titulo[:57] + '...'
        return titulo
    titulo_display.short_description = 'Título'

    def preview_imagem(self, obj):
        url = obj.get_imagem()
        if url and url != '/static/images/no-image.png':
            return format_html(
                '<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;" />',
                url
            )
        return '-'
    preview_imagem.short_description = 'Imagem'

    def preview_imagem_grande(self, obj):
        url = obj.get_imagem()
        if url and url != '/static/images/no-image.png':
            return format_html(
                '<img src="{}" style="max-width:300px;max-height:300px;object-fit:contain;border-radius:8px;" />',
                url
            )
        return 'Nenhuma imagem extraída ainda'
    preview_imagem_grande.short_description = 'Preview da Imagem'

    def plataforma_badge(self, obj):
        """Exibe a plataforma com ícone e cor."""
        cores = {
            'mercado_livre': '#FFB100',
            'amazon': '#FF9900',
            'shopee': '#EE4D2D',
            'shein': '#010101',
            'outro': '#999999',
        }
        icones = {
            'mercado_livre': '🟨 ',
            'amazon': '🟧 ',
            'shopee': '🔴 ',
            'shein': '⬛ ',
            'outro': '❓ ',
        }
        plataforma_chave = obj.plataforma.chave if obj.plataforma else None
        color = cores.get(plataforma_chave, '#999')
        icone = icones.get(plataforma_chave, '')
        label = obj.plataforma.nome if obj.plataforma else 'Não detectada'
        
        return format_html(
            '<span style="background:{};color:white;padding:5px 10px;'
            'border-radius:8px;font-size:12px;font-weight:bold;display:inline-block;">'
            '{}{}</span>',
            color, icone, label
        )
    plataforma_badge.short_description = 'Plataforma'

    def status_badge(self, obj):
        colors = {
            'pendente': '#ff9800',
            'processando': '#2196f3',
            'sucesso': '#4caf50',
            'erro': '#f44336',
        }
        color = colors.get(obj.status_extracao, '#999')
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">{}</span>',
            color, obj.get_status_extracao_display()
        )
    status_badge.short_description = 'Status'

    def categoria_display(self, obj):
        """Exibe a categoria extraída automaticamente."""
        if obj.categoria:
            return format_html(
                '<span style="background:#673AB7;color:white;padding:3px 8px;'
                'border-radius:10px;font-size:11px;font-weight:bold;">📁 {}</span>',
                obj.categoria.nome
            )
        return format_html(
            '<span style="background:#999;color:white;padding:3px 8px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">❌ Não extraída</span>'
        )
    categoria_display.short_description = 'Categoria'

    def save_model(self, request, obj, form, change):
        """Ao salvar, marcara origem como AUTOMÁTICO e extrai dados do link."""
        from .models import OrigemProduto
        
        # Sempre marcar como automático nesta interface
        obj.origem = OrigemProduto.AUTOMATICO
        
        is_new = not obj.pk
        link_changed = False

        if not is_new:
            try:
                old = ProdutoAutomatico.objects.get(pk=obj.pk)
                link_changed = old.link_afiliado != obj.link_afiliado
            except ProdutoAutomatico.DoesNotExist:
                is_new = True

        super().save_model(request, obj, form, change)

        # SEMPRE chamar para contar as tentativas
        if is_new or link_changed or True:  # ← Sempre executa
            from .scraper import processar_produto_automatico
            success = processar_produto_automatico(obj)
            
            # Recarregar para pegar dados atualizados
            obj.refresh_from_db()
            
            if success:
                messages.success(
                    request,
                    f'✅ Dados extraídos com sucesso para: {obj.titulo}'
                )
            else:
                # Mostrar contador de falhas
                if obj.ativo:
                    messages.warning(
                        request,
                        f'❌ Erro ao extrair dados. Tentativa {obj.falhas_consecutivas}/2. '
                        f'Verifique o link. Próxima falha desativa o produto. '
                        f'Erro: {obj.erro_extracao[:80]}'
                    )
                else:
                    messages.error(
                        request,
                        f'🛑 Produto DESATIVADO após {obj.falhas_consecutivas} tentativas. '
                        f'Corrija o link e clique em "Resetar contador de falhas" para tentar novamente. '
                        f'Motivo: {obj.motivo_desativacao[:80]}...'
                    )

    @admin.action(description='Extrair/Atualizar dados (Genérico - todas as plataformas)')
    def extrair_dados_action(self, request, queryset):
        """Extrai dados de todos os produtos selecionados."""
        from .scraper import processar_produto_automatico
        from .task_queue import queue_batch_tasks
        
        count = queryset.count()
        
        if count == 0:
            messages.warning(request, 'Nenhum produto selecionado.')
            return
        
        queue_batch_tasks(processar_produto_automatico, list(queryset))
        
        messages.success(
            request,
            f'✅ {count} produto(s) enfileirado(s) para extração. '
            f'Processamento acontecendo em background (multi-plataforma: ML, Amazon, Shopee, Shein)...'
        )

    @admin.action(description='Re-extrair dados (forçar atualização - todas as plataformas)')
    def reextrair_dados_action(self, request, queryset):
        """Força re-extração de dados, resetando status para PROCESSANDO."""
        from .models import StatusExtracao
        from .task_queue import queue_batch_tasks
        from .scraper import processar_produto_automatico
        
        queryset.update(status_extracao=StatusExtracao.PROCESSANDO)
        count = queryset.count()
        queue_batch_tasks(processar_produto_automatico, list(queryset))
        
        messages.success(
            request,
            f'✅ Forçada re-extração de {count} produto(s). '
            f'Processamento em background (multi-plataforma)...'
        )
    
    @admin.action(description='Resetar contador de falhas e reativar')
    def resetar_falhas_action(self, request, queryset):
        """Reseta contador de falhas e reativa produtos."""
        atualizado = queryset.update(
            falhas_consecutivas=0,
            motivo_desativacao='',
            ativo=True
        )
        messages.success(
            request,
            f'✅ {atualizado} produto(s) reativado(s) e contador de falhas resetado.'
        )

    @admin.action(description='📥 Importar múltiplos produtos via arquivo .txt')
    def importar_produtos_arquivo_action(self, request, queryset):
        """Abre formulário para importar múltiplos produtos via arquivo com vários links."""
        from django.urls import reverse
        from django.http import HttpResponseRedirect
        
        # Construir URL customizada de importação
        # A URL é registrada em get_urls() com nome 'importar_produtos_arquivo'
        # Django auto-prefixo o namespace do admin, então precisamos construir manualmente
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        url_name = f'admin:{app_label}_{model_name}_importar_produtos_arquivo'
        
        try:
            url = reverse(url_name)
        except:
            # Fallback: construir URL manualmente
            url = f'/admin/{app_label}/{model_name}/importar-arquivo/'
        
        return HttpResponseRedirect(url)

    def get_urls(self):
        """Adicionar URL customizada para importação de arquivo."""
        from django.urls import path
        urls = super().get_urls()
        app_label = self.model._meta.app_label
        model_name = self.model._meta.model_name
        custom_urls = [
            path('importar-arquivo/', self.admin_site.admin_view(self.processar_importacao_arquivo), 
                 name=f'{app_label}_{model_name}_importar_produtos_arquivo'),
        ]
        return custom_urls + urls

    def processar_importacao_arquivo(self, request):
        """View para processar upload de arquivo .txt com múltiplos links."""
        from django.shortcuts import render
        from .forms import ImportarProdutosForm
        from django.http import HttpResponseRedirect
        from django.urls import reverse
        
        if request.method == 'POST':
            form = ImportarProdutosForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    links = form.processar_arquivo()
                    processar_imediatamente = form.cleaned_data.get('processar_imediatamente', False)
                    
                    # Criar produtos para cada link
                    produtos_criados = []
                    produtos_duplicados = []
                    
                    from .models import OrigemProduto
                    from .scraper import processar_produto_automatico
                    from .task_queue import queue_batch_tasks
                    
                    for link in links:
                        # Verificar se já existe
                        existente = ProdutoAutomatico.objects.filter(link_afiliado=link).exists()
                        if existente:
                            produtos_duplicados.append(link)
                            continue
                        
                        # Criar novo produto
                        produto = ProdutoAutomatico.objects.create(
                            link_afiliado=link,
                            origem=OrigemProduto.AUTOMATICO,
                            ativo=True
                        )
                        produtos_criados.append(produto)
                    
                    # Processar produtos se solicitado
                    if processar_imediatamente and produtos_criados:
                        logger.info(f"📥 Importação: Enfileirando {len(produtos_criados)} para processamento automático")
                        queue_batch_tasks(processar_produto_automatico, produtos_criados)
                        messages.success(
                            request,
                            f'✅ {len(produtos_criados)} produto(s) criado(s) e enfileirado(s) para '
                            f'extração automática em background (por plataforma: ML, Amazon, Shopee, Shein). '
                            f'Processamento em andamento...'
                        )
                    else:
                        logger.info(f"📥 Importação: {len(produtos_criados)} produtos criados SEM enfileiramento")
                        messages.success(
                            request,
                            f'✅ {len(produtos_criados)} produto(s) criado(s) com sucesso. '
                            f'Execute a ação "Extrair dados" para processar.'
                        )
                    
                    if produtos_duplicados:
                        messages.warning(
                            request,
                            f'⚠️ {len(produtos_duplicados)} link(s) já existente(s) e foi(ram) ignorado(s).'
                        )
                    
                    # Redirecionar para listagem
                    return HttpResponseRedirect(reverse('admin:produtos_produtoautomaticoproxy_changelist'))
                    
                except Exception as e:
                    messages.error(request, f'❌ Erro ao processar arquivo: {str(e)}')
        else:
            form = ImportarProdutosForm()
        
        # Renderizar template customizado
        context = {
            'form': form,
            'title': 'Importar Múltiplos Produtos',
            'opts': self.model._meta,
            'has_view_permission': True,
        }
        return render(request, 'admin/importar_produtos.html', context)


@admin.register(ProdutoManualProxy)
class ProdutoManualProxyAdmin(admin.ModelAdmin):
    """Interface para criar/editar produtos manualmente.
    
    - Todos os campos são editáveis
    - Link é opcional (pode ser preenchido depois para extração)
    - Ideal para ajustar dados ou criar produtos sem link
    """
    list_display = (
        'titulo', 'preview_imagem', 'preco', 'categoria',
        'origem_badge', 'destaque', 'ativo', 'ordem', 'criado_em'
    )
    list_filter = ('ativo', 'destaque', 'categoria')
    search_fields = ('titulo', 'link_afiliado')
    list_editable = ('destaque', 'ativo', 'ordem')
    list_per_page = 25
    ordering = ('-destaque', 'ordem', '-criado_em')
    readonly_fields = ('preview_imagem_grande', 'criado_em', 'atualizado_em', 'origem_badge')

    fieldsets = (
        ('Informações do Produto', {
            'fields': ('titulo', 'categoria', 'plataforma', 'preco', 'preco_original', 'origem_badge'),
            'description': 'Preencha manualmente os dados do produto. Deixe "Link Afiliado" em branco se não tiver.'
        }),
        ('Imagem', {
            'fields': ('imagem_url', 'preview_imagem_grande'),
            'description': 'Cole a URL da imagem do produto. A URL tem prioridade.'
        }),
        ('Link Afiliado (Opcional)', {
            'fields': ('link_afiliado',),
            'description': 'Se preencher o link, você pode usar "Sincronizar com Automático" para extrair dados. Deixe em branco se for manual.'
        }),
        ('Descrição e URL Final', {
            'fields': ('descricao', 'url_final'),
            'classes': ('collapse',),
            'description': 'Campos opcionais para dados adicionais'
        }),
        ('Exibição', {
            'fields': ('destaque', 'ativo', 'ordem')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Mostrar produtos manuais E automáticos para poder editar tudo manualmente."""
        qs = super().get_queryset(request)
        # Não filtrar por origem - mostrar tudo para permitir edição manual
        return qs

    def preview_imagem(self, obj):
        url = obj.get_imagem()
        if url and url != '/static/images/no-image.png':
            return format_html(
                '<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;" />',
                url
            )
        return '-'
    preview_imagem.short_description = 'Imagem'

    def preview_imagem_grande(self, obj):
        url = obj.get_imagem()
        if url and url != '/static/images/no-image.png':
            return format_html(
                '<img src="{}" style="max-width:300px;max-height:300px;object-fit:contain;border-radius:8px;" />',
                url
            )
        return 'Nenhuma imagem'
    preview_imagem_grande.short_description = 'Preview'

    def origem_badge(self, obj):
        """Exibe a origem do produto."""
        return format_html(
            '<span style="background:#607D8B;color:white;padding:3px 8px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">{}</span>',
            obj.get_origem_display()
        )
    origem_badge.short_description = 'Origem'

    def save_model(self, request, obj, form, change):
        """Ao salvar, marca origem como MANUAL apenas se for novo produto."""
        from .models import OrigemProduto
        
        # Se é novo produto, marcar como MANUAL
        if not change:
            obj.origem = OrigemProduto.MANUAL
        # Se é existente, PRESERVAR a origem (não mudar)
        
        super().save_model(request, obj, form, change)
        
        # Mostrar mensagem diferenciada
        if change:
            messages.success(
                request,
                f'✅ Produto "{obj.titulo}" atualizado com sucesso. '
                f'Origem preservada como {obj.get_origem_display().lower()}.'
            )
        else:
            messages.success(
                request,
                f'✅ Novo produto manual "{obj.titulo}" criado com sucesso. '
                f'Você pode preencher o link depois e sincronizar com extração automática.'
            )


# ============================================================
# AGENDAMENTO DE ATUALIZAÇÃO AUTOMÁTICA
# ============================================================

class LogAtualizacaoInline(admin.TabularInline):
    """Inline para exibir os últimos logs dentro do agendamento."""
    model = LogAtualizacao
    extra = 0
    max_num = 10
    readonly_fields = (
        'executado_em', 'total_produtos', 'sucesso', 'erros',
        'duracao_segundos', 'detalhes'
    )
    can_delete = False
    ordering = ['-executado_em']

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AgendamentoAtualizacao)
class AgendamentoAtualizacaoAdmin(admin.ModelAdmin):
    list_display = (
        'nome', 'horario', 'dias_semana', 'ativo',
        'atualizar_apenas_ativos', 'ultimo_log_display', 'atualizado_em'
    )
    list_filter = ('ativo', 'dias_semana')
    list_editable = ('ativo',)
    search_fields = ('nome',)
    ordering = ('horario',)
    inlines = [LogAtualizacaoInline]
    actions = ['executar_agora_action', 'ativar_action', 'desativar_action']

    fieldsets = (
        ('Configuração do Agendamento', {
            'fields': ('nome', 'horario', 'dias_semana'),
            'description': (
                '<strong style="font-size:14px;color:#1a73e8;">'
                'Configure o horário e os dias em que a atualização '
                'automática dos preços será executada.</strong><br><br>'
                '<strong>Como funciona:</strong> O GCP Cloud Scheduler '
                '(ou cron) chama o endpoint <code>/api/atualizar-produtos/</code> '
                'a cada hora. O sistema verifica se há agendamentos ativos '
                'para o horário atual e executa a atualização.<br><br>'
                '<strong>Management command:</strong> '
                '<code>python manage.py atualizar_produtos_ml</code><br>'
                '<strong>Forçar execução:</strong> '
                '<code>python manage.py atualizar_produtos_ml --forcar</code>'
            )
        }),
        ('Controle', {
            'fields': ('ativo', 'atualizar_apenas_ativos')
        }),
    )

    def ativo_badge(self, obj):
        if obj.ativo:
            return format_html(
                '<span style="background:#4caf50;color:white;padding:3px 10px;'
                'border-radius:10px;font-size:11px;font-weight:bold;">'
                'ATIVO</span>'
            )
        return format_html(
            '<span style="background:#f44336;color:white;padding:3px 10px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">'
            'INATIVO</span>'
        )
    ativo_badge.short_description = 'Status'

    def ultimo_log_display(self, obj):
        log = obj.logs.order_by('-executado_em').first()
        if log:
            return format_html(
                '<span title="{}">{} - {}/{} OK ({:.0f}s)</span>',
                log.detalhes[:200] if log.detalhes else '',
                log.executado_em.strftime('%d/%m %H:%M'),
                log.sucesso,
                log.total_produtos,
                log.duracao_segundos
            )
        return '-'
    ultimo_log_display.short_description = 'Última Execução'

    @admin.action(description='Executar atualização AGORA')
    def executar_agora_action(self, request, queryset):
        """Executa a atualização imediatamente para os agendamentos selecionados."""
        import time
        from .scraper import processar_produto_automatico

        for ag in queryset:
            inicio = time.time()
            produtos = ProdutoAutomatico.objects.all()
            if ag.atualizar_apenas_ativos:
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
                        f'EXCEÇÃO: {produto.id} -> {str(e)[:80]}'
                    )

            duracao = time.time() - inicio

            LogAtualizacao.objects.create(
                agendamento=ag,
                total_produtos=total,
                sucesso=sucesso,
                erros=erros,
                detalhes='\n'.join(detalhes_list),
                duracao_segundos=round(duracao, 2)
            )

            messages.success(
                request,
                f'Agendamento "{ag.nome}" executado: '
                f'{sucesso}/{total} sucesso(s), {erros} erro(s) '
                f'em {duracao:.1f}s'
            )

    @admin.action(description='Ativar agendamentos selecionados')
    def ativar_action(self, request, queryset):
        updated = queryset.update(ativo=True)
        messages.success(request, f'{updated} agendamento(s) ativado(s).')

    @admin.action(description='Desativar agendamentos selecionados')
    def desativar_action(self, request, queryset):
        updated = queryset.update(ativo=False)
        messages.success(request, f'{updated} agendamento(s) desativado(s).')


@admin.register(LogAtualizacao)
class LogAtualizacaoAdmin(admin.ModelAdmin):
    list_display = (
        'executado_em', 'agendamento', 'total_produtos',
        'resultado_badge', 'duracao_segundos'
    )
    list_filter = ('agendamento', 'executado_em')
    readonly_fields = (
        'agendamento', 'executado_em', 'total_produtos',
        'sucesso', 'erros', 'detalhes', 'duracao_segundos'
    )
    ordering = ['-executado_em']
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def resultado_badge(self, obj):
        if obj.erros == 0:
            color = '#4caf50'
        elif obj.sucesso > 0:
            color = '#ff9800'
        else:
            color = '#f44336'
        return format_html(
            '<span style="background:{};color:white;padding:3px 8px;'
            'border-radius:10px;font-size:11px;font-weight:bold;">'
            '{} OK / {} Erros</span>',
            color, obj.sucesso, obj.erros
        )
    resultado_badge.short_description = 'Resultado'


@admin.register(DocumentoLegal)
class DocumentoLegalAdmin(admin.ModelAdmin):
    """Admin para gerenciar documentos legais: Privacidade, Termos e Afiliados."""
    list_display = ('get_tipo_display', 'atualizado_em', 'criado_em')
    list_filter = ('tipo',)
    readonly_fields = ('criado_em', 'atualizado_em', 'preview_html')
    search_fields = ('texto_html',)
    ordering = ('tipo',)

    fieldsets = (
        ('Informações', {
            'fields': ('tipo',)
        }),
        ('Conteúdo HTML', {
            'fields': ('texto_html', 'preview_html'),
            'description': 'Use tags HTML: &lt;p&gt;, &lt;h2&gt;, &lt;h3&gt;, &lt;b&gt;, &lt;i&gt;, &lt;ul&gt;, &lt;li&gt;, etc'
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def preview_html(self, obj):
        """Mostra preview do HTML no admin."""
        if not obj.pk:
            return "Salve o documento primeiro para ver o preview."
        return format_html(
            '<div style="border:1px solid #ddd;padding:15px;background:#f9f9f9;'
            'border-radius:5px;max-height:400px;overflow-y:auto;">{}</div>',
            obj.texto_html
        )
    preview_html.short_description = 'Preview do Conteúdo'

    def get_tipo_display(self, obj):
        return obj.get_tipo_display()
    get_tipo_display.short_description = 'Tipo de Documento'


# Personalizar o admin site
admin.site.site_header = 'Vendas Links Tops ML - Administração'
admin.site.site_title = 'Vendas Links Tops ML'
admin.site.index_title = 'Painel de Controle'


# ============================================================
# CONFIGURAÇÃO DE ESCALONAMENTO (Singleton)
# ============================================================

@admin.register(EscalonamentoConfig)
class EscalonamentoConfigAdmin(admin.ModelAdmin):
    """
    Admin para configurações de escalonamento.
    SINGLETON: Existe apenas 1 registro (pk=1).
    
    Permite ajustar LIMITE_FALHAS, NUM_WORKERS, timeouts e outros
    parâmetros em runtime, sem necessidade de redeploy.
    """

    # Campos readonly (não editáveis)
    readonly_fields = ('atualizado_em', 'config_summary')

    # Fieldsets organizados por seção
    fieldsets = (
        ('🎯 LIMITE DE FALHAS E RETRY BACKOFF', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Controla como o sistema '
                'lida com produtos que falham durante a extração.</strong><br><br>'
                '✅ <strong>Aumente limite_falhas</strong> para reduzir falsos positivos '
                '(ex: timeout ocasional)<br>'
                '✅ <strong>Aumente retry_delays</strong> para evitar rate limiting<br>'
                '⚠️ <strong>Diminua</strong ambos para desativar rápido produtos problemáticos. '
                '<br><br>'
                '<code style="background:#f5f5f5;padding:3px 6px;">Ex: 3 falhas cada 5min, '
                '15min, 1h, 4h = 5 tentativas totais com backoff exponencial</code>'
            ),
            'fields': (
                'limite_falhas',
                'retry_delay_1_minutos',
                'retry_delay_2_minutos',
                'retry_delay_3_minutos',
                'retry_delay_4_minutos',
            ),
        }),
        ('⚙️ PROCESSAMENTO E WORKERS', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Controla paralelismo e fila.</strong><br><br>'
                '🔧 <strong>num_workers</strong>: Threads paralelas. Dev=2, Staging=4, Prod=8+<br>'
                '🔧 <strong>max_queue_size</strong>: Máximo de tarefas pendentes<br>'
                '🔧 <strong>task_timeout_segundos</strong>: Timeout por tarefa (reduzir se der timeout frequente)'
            ),
            'fields': (
                'num_workers',
                'max_queue_size',
                'task_timeout_segundos',
            ),
        }),
        ('🌐 PLAYWRIGHT (Web Scraping)', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Timeout e delays para extrair dados de páginas web.</strong><br><br>'
                '⏱️ <strong>playwright_timeout_ms</strong>: Tempo máximo para carregar página (30s é padrão)<br>'
                '⏱️ <strong>playwright_delay_ms</strong>: Esperar após carregar (para JavaScript render)'
            ),
            'fields': (
                'playwright_timeout_ms',
                'playwright_delay_ms',
            ),
        }),
        ('🚦 RATE LIMITING', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Protege contra banimento das plataformas.</strong><br><br>'
                'Aumentar delays se tomar muitos 429 (Too Many Requests). '
                'Reduzir para ir mais rápido se estabilizar.'
            ),
            'fields': (
                'rate_limit_delay_ms',
                'max_concurrent_requests',
            ),
        }),
        ('💾 DATABASE', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Configurações de banco de dados.</strong><br><br>'
                '⚠️ <strong>use_sqlite</strong>: APENAS para dev local. '
                'Produção com 1000+ itens: <strong>SEMPRE MySQL/PostgreSQL</strong><br>'
                'ℹ️ Em production, settings.py carrega esse valor via env var.'
            ),
            'fields': (
                'use_sqlite',
                'sqlite_timeout_segundos',
            ),
        }),
        ('📋 LOGGING', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Verbosidade de logs.</strong><br><br>'
                '🐛 DEBUG: Muitos detalhes (dev local)<br>'
                'ℹ️ INFO: Informações principais (recomendado prod)<br>'
                '⚠️ WARNING: Apenas alertas<br>'
                '❌ ERROR: Apenas erros'
            ),
            'fields': (
                'log_level',
                'logs_retention_dias',
            ),
        }),
        ('� SEGURANÇA', {
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Configurações de segurança de sessão.</strong><br><br>'
                '⏱️ <strong>Timeout de Logout</strong>: Tempo de inatividade antes de logout automático<br>'
                '⚠️ Valores baixos (10min) = mais seguro mas inconveniente<br>'
                '✅ Recomendado: 30 minutos para balancear segurança e UX'
            ),
            'fields': (
                'session_timeout_minutos',
            ),
        }),
        ('�📝 NOTAS E HISTÓRICO', {
            'classes': ('wide',),
            'description': (
                '<strong style="font-size:13px;color:#2196f3;">Documenterenomudanças.</strong><br>'
                'Ex: "Aumentado retry_delay_1 de 5 para 10 → muitos timeouts na Shopee 2026-03-20"'
            ),
            'fields': (
                'nota',
                'atualizado_em',
                'config_summary',
            ),
        }),
    )

    def config_summary(self, obj):
        """Exibe um resumo da configuração atual."""
        from .config_escalonamento import get_config_info
        config_text = get_config_info()  # Será criada função helper
        return format_html(
            '<pre style="background:#f5f5f5;padding:12px;border-radius:5px;'
            'font-size:11px;line-height:1.6;max-height:300px;overflow-y:auto;"'
            'font-family:monospace;">{}</pre>',
            config_text
        )
    config_summary.short_description = '📊 Resumo da Configuração Atual'

    def has_add_permission(self, request):
        """Impede criar novos registros (singleton)"""
        # Permitir add apenas se não existir nenhum registro
        from .models import EscalonamentoConfig
        return not EscalonamentoConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """Impede deletar configuração"""
        return False

    def save_model(self, request, obj, form, change):
        """Força sempre salvar com pk=1 (singleton)"""
        obj.pk = 1
        super().save_model(request, obj, form, change)
        
        # Mostrar mensagem confirmando salva
        from django.contrib import messages
        messages.success(
            request,
            '✅ Configuração de escalonamento atualizada com sucesso! '
            'As mudanças entram em efeito no próximo ciclo de processamento.'
        )

    def get_urls(self):
        """Adiciona URL para ir direto à configuração (singleton)"""
        from django.urls import path
        from django.views.decorators.http import require_http_methods
        
        urls = super().get_urls()
        
        # No list view, redirecionar para edit do único registro
        custom_urls = [
            path(
                '',
                require_http_methods(['GET'])(self.admin_site.admin_view(self.singleton_redirect)),
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_changelist',
            ),
        ]
        
        return custom_urls + urls
    
    def singleton_redirect(self, request):
        """Redireciona list view → edit da config única"""
        from django.shortcuts import redirect
        from .models import EscalonamentoConfig
        
        config = EscalonamentoConfig.obter_config()
        return redirect(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', config.pk)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'telefone', 'canal_preferido', 'ativo', 'criado_em')
    list_filter = ('ativo', 'canal_preferido', 'criado_em')
    search_fields = ('nome', 'email')
    list_editable = ('ativo',)
    readonly_fields = ('criado_em', 'atualizado_em')
    ordering = ('-criado_em',)


@admin.register(SiteMaintenanceConfig)
class SiteMaintenanceConfigAdmin(admin.ModelAdmin):
    """Admin para configuração de manutenção do site - Singleton.
    
    Sempre mostra o único registro. Ao acessar a listagem, redireciona direto para editar.
    """
    
    list_display = ('status_display', 'titulo', 'tempo_estimado_display', 'atualizado_em')
    readonly_fields = ('criado_em', 'atualizado_em')
    
    fieldsets = (
        ('🔴 STATUS DE MANUTENÇÃO', {
            'fields': ('em_manutencao',),
            'description': (
                '<strong style="font-size:14px;color:#d32f2f;">Marque para ATIVAR o modo de manutenção. '
                'Todos os visitantes verão a página de manutenção em vez do site normal.</strong>'
            )
        }),
        ('📝 MENSAGENS', {
            'fields': ('titulo', 'mensagem', 'email_contato'),
            'description': (
                'Customize a mensagem exibida aos clientes. '
                'A mensagem suporta HTML básico (<strong>p</strong>, <strong>h2</strong>, <strong>h3</strong>, <strong>br</strong>, <strong>b</strong>, <strong>i</strong>, etc)'
            )
        }),
        ('⏱️ DURAÇÃO ESTIMADA', {
            'fields': ('tempo_estimado_minutos', 'mostrar_tempo_estimado'),
            'description': 'Digite o tempo estimado em minutos. Será exibido como "Tempo estimado: X min".'
        }),
        ('📅 CONTROLE', {
            'fields': ('data_inicio', 'criado_em', 'atualizado_em'),
            'description': 'Data de início é preenchida automaticamente quando ativa a manutenção.'
        }),
    )
    
    def status_display(self, obj):
        """Exibe status visual com emoji."""
        if obj.em_manutencao:
            return format_html(
                '<span style="background:#d32f2f;color:white;padding:5px 12px;'
                'border-radius:20px;font-weight:bold;display:inline-block;">🔴 MANUTENÇÃO ATIVA</span>'
            )
        return format_html(
            '<span style="background:#388e3c;color:white;padding:5px 12px;'
            'border-radius:20px;font-weight:bold;display:inline-block;">🟢 SITE OPERACIONAL</span>'
        )
    status_display.short_description = 'Status'
    
    def tempo_estimado_display(self, obj):
        """Exibe tempo estimado formatado."""
        if obj.mostrar_tempo_estimado:
            return f"{obj.tempo_estimado_minutos} min"
        return "-"
    tempo_estimado_display.short_description = 'Retorno Estimado'
    
    def save_model(self, request, obj, form, change):
        """Ao salvar, registra data de início se ativando manutenção."""
        if obj.em_manutencao and not obj.data_inicio:
            from django.utils import timezone
            obj.data_inicio = timezone.now()
        
        super().save_model(request, obj, form, change)
        
        # Mensagem feedback
        if obj.em_manutencao:
            messages.warning(
                request,
                f'⚠️ MANUTENÇÃO ATIVADA! Site exibindo página de manutenção. '
                f'Retorno estimado: {obj.tempo_estimado_minutos} minutos.'
            )
        else:
            messages.success(
                request,
                '✅ Manutenção desativada. Site retornando ao normal.'
            )
    
    def has_delete_permission(self, request, obj=None):
        """Impede exclusão do registro."""
        return False
    
    def has_add_permission(self, request):
        """Não permite criar novos registros."""
        return False
    
    def get_urls(self):
        """Redireciona list view direto para edit do único registro."""
        from django.urls import path
        from django.views.decorators.http import require_http_methods
        
        urls = super().get_urls()
        
        custom_urls = [
            path(
                '',
                require_http_methods(['GET'])(self.admin_site.admin_view(self.singleton_redirect)),
                name=f'{self.model._meta.app_label}_{self.model._meta.model_name}_changelist',
            ),
        ]
        
        return custom_urls + urls
    
    def singleton_redirect(self, request):
        """Redireciona list view → edit da config única."""
        from django.shortcuts import redirect
        
        config = SiteMaintenanceConfig.get_config()
        return redirect(f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change', config.pk)
