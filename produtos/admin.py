from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import (
    Produto, Categoria, Anuncio, ProdutoAutomatico,
    AgendamentoAtualizacao, LogAtualizacao, DocumentoLegal
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug', 'ativo', 'ordem', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('nome',)
    list_editable = ('ativo', 'ordem')
    prepopulated_fields = {'slug': ('nome',)}
    ordering = ('ordem', 'nome')


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 'preview_imagem', 'preco', 'categoria',
        'destaque', 'ativo', 'ordem', 'criado_em'
    )
    list_filter = ('ativo', 'destaque', 'categoria')
    search_fields = ('titulo',)
    list_editable = ('destaque', 'ativo', 'ordem')
    list_per_page = 25
    ordering = ('-destaque', 'ordem', '-criado_em')
    readonly_fields = ('preview_imagem_grande', 'criado_em', 'atualizado_em')

    fieldsets = (
        ('Informações do Produto', {
            'fields': ('titulo', 'categoria', 'preco', 'preco_original')
        }),
        ('Imagem', {
            'fields': ('imagem', 'imagem_url', 'preview_imagem_grande'),
            'description': 'Use upload OU URL externa. O upload tem prioridade.'
        }),
        ('Link Afiliado', {
            'fields': ('link_afiliado',)
        }),
        ('Exibição', {
            'fields': ('destaque', 'ativo', 'ordem')
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

    def preview_imagem(self, obj):
        url = obj.get_imagem()
        if url:
            return format_html(
                '<img src="{}" style="width:50px;height:50px;object-fit:cover;border-radius:4px;" />',
                url
            )
        return '-'
    preview_imagem.short_description = 'Imagem'

    def preview_imagem_grande(self, obj):
        url = obj.get_imagem()
        if url:
            return format_html(
                '<img src="{}" style="max-width:300px;max-height:300px;object-fit:contain;border-radius:8px;" />',
                url
            )
        return 'Nenhuma imagem'
    preview_imagem_grande.short_description = 'Preview'


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


@admin.register(ProdutoAutomatico)
class ProdutoAutomaticoAdmin(admin.ModelAdmin):
    list_display = (
        'titulo_display', 'plataforma_badge', 'preview_imagem', 'preco', 'status_badge',
        'falhas_consecutivas', 'categoria', 'destaque', 'ativo', 'ordem', 'criado_em'
    )
    list_filter = ('plataforma', 'status_extracao', 'ativo', 'destaque', 'categoria', 'falhas_consecutivas')
    search_fields = ('titulo', 'link_afiliado')
    list_editable = ('destaque', 'ativo', 'ordem')
    list_per_page = 25
    ordering = ('-destaque', 'ordem', '-criado_em')
    readonly_fields = (
        'plataforma', 'titulo', 'imagem_url', 'preco', 'preco_original', 'descricao',
        'url_final', 'status_extracao', 'erro_extracao',
        'preview_imagem_grande', 'criado_em', 'atualizado_em', 'ultima_extracao',
        'falhas_consecutivas', 'motivo_desativacao'
    )
    actions = ['extrair_dados_action', 'reextrair_dados_action', 'resetar_falhas_action']

    fieldsets = (
        ('Link do Produto (COLE AQUI)', {
            'fields': ('link_afiliado', 'plataforma'),
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
            'description': 'Estes campos são preenchidos automaticamente pelo sistema.'
        }),
        ('Configuração Manual', {
            'fields': ('categoria', 'destaque', 'ativo', 'ordem')
        }),
        ('Status da Extração', {
            'fields': ('status_extracao', 'erro_extracao', 'ultima_extracao'),
            'classes': ('collapse',)
        }),
        ('Monitoramento de Falhas', {
            'fields': ('falhas_consecutivas', 'motivo_desativacao'),
            'description': 'Produto é desativado automaticamente após 2 falhas consecutivas'
        }),
        ('Datas', {
            'fields': ('criado_em', 'atualizado_em'),
            'classes': ('collapse',)
        }),
    )

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
        color = cores.get(obj.plataforma, '#999')
        icone = icones.get(obj.plataforma, '')
        label = obj.get_plataforma_display() if obj.plataforma else 'Não detectada'
        
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

    def save_model(self, request, obj, form, change):
        """Ao salvar, SEMPRE tentar extrair dados do link.
        
        Se link é novo ou mudou, extrai automaticamente.
        Se link não mudou mas salvou novamente, também extrai (conta tentativas).
        """
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
        # (não apenas quando link muda)
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
        """
        Extrai dados de todos os produtos selecionados (ML, Amazon, Shopee, Shein, etc).
        Processamento assíncrono para evitar bloqueios com múltiplas plataformas.
        """
        from .scraper import processar_produto_automatico
        from .task_queue import queue_batch_tasks
        
        count = queryset.count()
        
        if count == 0:
            messages.warning(request, 'Nenhum produto selecionado.')
            return
        
        # Adicionar tarefas à fila para processamento assíncrono
        queue_batch_tasks(processar_produto_automatico, list(queryset))
        
        messages.success(
            request,
            f'✅ {count} produto(s) enfileirado(s) para extração. '
            f'Processamento acontecendo em background (multi-plataforma: ML, Amazon, Shopee, Shein)...'
        )

    @admin.action(description='Re-extrair dados (forçar atualização - todas as plataformas)')
    def reextrair_dados_action(self, request, queryset):
        """
        Força re-extração de dados, resetando status para PROCESSANDO.
        """
        from .models import StatusExtracao
        from .task_queue import queue_batch_tasks
        from .scraper import processar_produto_automatico
        
        # Resetar status para forçar re-extração
        queryset.update(status_extracao=StatusExtracao.PROCESSANDO)
        
        count = queryset.count()
        
        # Enfileirar para processamento assíncrono
        queue_batch_tasks(processar_produto_automatico, list(queryset))
        
        messages.success(
            request,
            f'✅ Forçada re-extração de {count} produto(s). '
            f'Processamento em background (multi-plataforma)...'
        )
    
    @admin.action(description='Resetar contador de falhas e reativar')
    def resetar_falhas_action(self, request, queryset):
        """
        Reseta contador de falhas e reativa produtos (todas as plataformas).
        """
        atualizado = queryset.update(
            falhas_consecutivas=0,
            motivo_desativacao='',
            ativo=True  # Reativar produtos desativados
        )
        messages.success(
            request,
            f'✅ {atualizado} produto(s) reativado(s) e contador de falhas resetado.'
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
