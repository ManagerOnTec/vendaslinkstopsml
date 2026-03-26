from django.db import models
from django.utils.text import slugify


class Categoria(models.Model):
    """Categorias de produtos para organização e filtros."""
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição (menor = primeiro)")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['ordem', 'nome']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


# ============================================================
# ARQUITETURA DE PRODUTOS - Unificado
# ============================================================
# Nota: O modelo "Produto" simples (origem manual) foi consolidado em ProdutoAutomatico.
# Agora há um único modelo com proxy models para diferentes interfaces:
# - ProdutoAutomaticoProxy: Para criar via link (extração automática)
# - ProdutoManualProxy: Para criar manualmente ou editar dados extraídos


class PosicaoAnuncio(models.TextChoices):
    TOPO = 'topo', 'Topo da Página'
    MEIO = 'meio', 'Entre Produtos'
    RODAPE = 'rodape', 'Rodapé da Página'
    LATERAL = 'lateral', 'Lateral'


class Anuncio(models.Model):
    """Blocos de anúncios (AdSense) gerenciáveis via admin."""
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome do Anúncio",
        help_text="Nome interno para identificação"
    )
    codigo_html = models.TextField(
        verbose_name="Código HTML",
        help_text="Cole aqui o script do Google AdSense ou outro código de anúncio"
    )
    posicao = models.CharField(
        max_length=20,
        choices=PosicaoAnuncio.choices,
        default=PosicaoAnuncio.MEIO,
        verbose_name="Posição"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo"
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Ordem de exibição dentro da posição"
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        verbose_name = "Anúncio"
        verbose_name_plural = "Anúncios"
        ordering = ['posicao', 'ordem']

    def __str__(self):
        return f"{self.nome} ({self.get_posicao_display()})"


class Plataforma(models.TextChoices):
    """Plataformas de e-commerce suportadas."""
    MERCADO_LIVRE = 'mercado_livre', 'Mercado Livre'
    AMAZON = 'amazon', 'Amazon'
    SHOPEE = 'shopee', 'Shopee'
    SHEIN = 'shein', 'Shein'
    OUTRO = 'outro', 'Outro'


class StatusExtracao(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    PROCESSANDO = 'processando', 'Processando...'
    SUCESSO = 'sucesso', 'Extraído com Sucesso'
    ERRO = 'erro', 'Erro na Extração'


class OrigemProduto(models.TextChoices):
    """Indica a origem da criação do produto."""
    AUTOMATICO = 'automatico', 'Extraído Automaticamente'
    MANUAL = 'manual', 'Criado Manualmente'


class ProdutoAutomatico(models.Model):
    """Modelo unificado de Produto com suporte a extração automática e edição manual.
    
    Pode ser criado/editado de duas formas:
    1. AUTOMÁTICO (via link): Sistema extrai automaticamente título, imagem, preço
    2. MANUAL: Usuário cria/edita manualmente (pode ter link ou não)
    
    Usa proxy models para diferentes interfaces de admin:
    - ProdutoAutomatico: Interface para criar/atualizar via link (extração)
    - ProdutoManual: Interface para criar/editar manualmente (campos editáveis)
    """
    origem = models.CharField(
        max_length=20,
        choices=OrigemProduto.choices,
        default=OrigemProduto.AUTOMATICO,
        verbose_name="Origem",
        help_text="Indica se foi extraído automaticamente ou criado manualmente",
        db_index=True
    )
    link_afiliado = models.URLField(
        max_length=3000,
        verbose_name="Link Afiliado",
        help_text="Cole o link do produto (Mercado Livre, Amazon, Shopee, Shein, etc) ou deixe em branco para manual"
    )
    # Plataforma detectada
    plataforma = models.CharField(
        max_length=20,
        choices=Plataforma.choices,
        default=Plataforma.OUTRO,
        verbose_name="Plataforma",
        help_text="Detectada automaticamente pela URL do link"
    )
    # Campos extraídos automaticamente
    titulo = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Título",
        help_text="Extraído automaticamente"
    )
    imagem_url = models.URLField(
        max_length=3000,
        blank=True,
        verbose_name="URL da Imagem",
        help_text="Extraída automaticamente"
    )
    preco = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Preço",
        help_text="Extraído automaticamente"
    )
    preco_original = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Preço Original",
        help_text="Preço antes do desconto (se houver)"
    )
    descricao = models.TextField(
        blank=True,
        verbose_name="Descrição",
        help_text="Extraída automaticamente"
    )
    url_final = models.URLField(
        max_length=3000,
        blank=True,
        verbose_name="URL Final do Produto",
        help_text="URL real do produto após redirecionamentos"
    )
    # Campos de controle
    status_extracao = models.CharField(
        max_length=20,
        choices=StatusExtracao.choices,
        default=StatusExtracao.PENDENTE,
        verbose_name="Status da Extração",
        db_index=True  # ← ÍNDICE ADICIONADO
    )
    erro_extracao = models.TextField(
        blank=True,
        verbose_name="Erro da Extração",
        help_text="Detalhes do erro caso a extração falhe"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos_automaticos',
        verbose_name="Categoria"
    )
    destaque = models.BooleanField(
        default=False,
        verbose_name="Destaque"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        db_index=True  # ← ÍNDICE ADICIONADO
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem"
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    ultima_extracao = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última Extração",
        db_index=True  # ← ÍNDICE ADICIONADO
    )
    falhas_consecutivas = models.IntegerField(
        default=0,
        verbose_name="Falhas Consecutivas",
        help_text="Número de tentativas de atualização que falharam. Ao atingir limite, produto é desativado automaticamente.",
        db_index=True  # ← ÍNDICE ADICIONADO
    )
    motivo_desativacao = models.TextField(
        blank=True,
        verbose_name="Motivo da Desativação",
        help_text="Registra o motivo automático de desativação (ex: falhas consecutivas)"
    )

    class Meta:
        verbose_name = "Produto Automático"
        verbose_name_plural = "Produtos Automáticos"
        ordering = ['-destaque', 'ordem', '-criado_em']
        indexes = [
            models.Index(fields=['ativo', 'status_extracao'], name='idx_ativo_status'),
            models.Index(fields=['-ultima_extracao', 'ativo'], name='idx_ultima_ext_ativo'),
            models.Index(fields=['falhas_consecutivas', 'ativo'], name='idx_falhas_ativo'),
            models.Index(fields=['plataforma', 'ativo'], name='idx_plataforma_ativo'),
        ]

    def get_imagem(self):
        """Retorna a URL da imagem extraída."""
        return self.imagem_url or '/static/images/no-image.png'

    def __str__(self):
        return self.titulo or f"Produto (link: {self.link_afiliado[:50] if self.link_afiliado else 'manual'}...)"


# ============================================================
# PROXY MODELS - Diferentes interfaces de admin
# ============================================================

class ProdutoAutomaticoProxy(ProdutoAutomatico):
    """Proxy model para interface de extração automática.
    
    Ao criar/editar nesta interface:
    - Link é obrigatório
    - Título, imagem, preço são readonly (extraídos automaticamente)
    - origem = AUTOMATICO
    """
    class Meta:
        proxy = True
        verbose_name = "Produto Automático"
        verbose_name_plural = "Produtos Automáticos"
        ordering = ['-destaque', 'ordem', '-criado_em']


class ProdutoManualProxy(ProdutoAutomatico):
    """Proxy model para interface de criação/edição manual.
    
    Ao criar/editar nesta interface:
    - Todos os campos são editáveis
    - Link é opcional (pode ser preenchido depois para extração)
    - origem = MANUAL
    - Permite ajustar dados extraídos automaticamente
    """
    class Meta:
        proxy = True
        verbose_name = "Produto Manual"
        verbose_name_plural = "Produtos Manuais"
        ordering = ['-destaque', 'ordem', '-criado_em']


# ============================================================
# COMPATIBILIDADE - Remover classe antiga Produto
# ============================================================
# Nota: O modelo "Produto" simples foi consolidado em ProdutoAutomatico.
# As migrations vão migrar dados se houver.


class DiaSemana(models.TextChoices):
    TODOS = 'todos', 'Todos os dias'
    SEG = 'seg', 'Segunda-feira'
    TER = 'ter', 'Terça-feira'
    QUA = 'qua', 'Quarta-feira'
    QUI = 'qui', 'Quinta-feira'
    SEX = 'sex', 'Sexta-feira'
    SAB = 'sab', 'Sábado'
    DOM = 'dom', 'Domingo'
    SEG_SEX = 'seg_sex', 'Segunda a Sexta'


class AgendamentoAtualizacao(models.Model):
    """Agendamento para atualização automática de preços dos produtos do ML.
    Cadastre o horário desejado e ative/desative conforme necessário.
    O Cloud Scheduler (ou cron) chama o endpoint/command e o sistema
    verifica se há agendamentos ativos para o horário atual."""
    nome = models.CharField(
        max_length=100,
        verbose_name="Nome do Agendamento",
        help_text="Nome para identificação (ex: 'Atualização Manhã', 'Atualização Noite')"
    )
    horario = models.TimeField(
        verbose_name="Horário de Execução",
        help_text="Horário em que a atualização será executada (ex: 08:00, 14:00, 20:00)"
    )
    dias_semana = models.CharField(
        max_length=10,
        choices=DiaSemana.choices,
        default=DiaSemana.TODOS,
        verbose_name="Dias da Semana",
        help_text="Em quais dias este agendamento deve rodar"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Ative ou desative este agendamento"
    )
    atualizar_apenas_ativos = models.BooleanField(
        default=True,
        verbose_name="Apenas produtos ativos",
        help_text="Se marcado, atualiza apenas produtos com status 'Ativo'"
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Agendamento de Atualização"
        verbose_name_plural = "Agendamentos de Atualização"
        ordering = ['horario']

    def __str__(self):
        status = '✓' if self.ativo else '✗'
        return f"[{status}] {self.nome} - {self.horario.strftime('%H:%M')} ({self.get_dias_semana_display()})"


class LogAtualizacao(models.Model):
    """Log de execução das atualizações automáticas."""
    agendamento = models.ForeignKey(
        AgendamentoAtualizacao,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name="Agendamento",
        null=True,
        blank=True
    )
    executado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Executado em"
    )
    total_produtos = models.IntegerField(
        default=0,
        verbose_name="Total de Produtos"
    )
    sucesso = models.IntegerField(
        default=0,
        verbose_name="Sucesso"
    )
    erros = models.IntegerField(
        default=0,
        verbose_name="Erros"
    )
    detalhes = models.TextField(
        blank=True,
        verbose_name="Detalhes",
        help_text="Detalhes da execução"
    )
    duracao_segundos = models.FloatField(
        default=0,
        verbose_name="Duração (segundos)"
    )

    class Meta:
        verbose_name = "Log de Atualização"
        verbose_name_plural = "Logs de Atualização"
        ordering = ['-executado_em']

    def __str__(self):
        return f"{self.executado_em.strftime('%d/%m/%Y %H:%M')} - {self.sucesso}/{self.total_produtos} OK"


class DocumentoLegal(models.Model):
    """Documentos legais: Políticas de Privacidade, Termos de Uso, Divulgação de Afiliados."""
    TITULOS_CHOICES = [
        ('privacidade', 'Política de Privacidade'),
        ('termos', 'Termos de Uso'),
        ('afiliados', 'Divulgação de Afiliados'),
    ]

    tipo = models.CharField(
        max_length=20,
        choices=TITULOS_CHOICES,
        unique=True,
        verbose_name="Tipo de Documento"
    )
    texto_html = models.TextField(
        help_text="Use HTML para formatar (tags: p, h2, h3, b, i, ul, li, etc)"
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização"
    )
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )

    class Meta:
        verbose_name = "Documento Legal"
        verbose_name_plural = "Documentos Legais"
        ordering = ['tipo']

    def __str__(self):
        return self.get_tipo_display()


class EscalonamentoConfig(models.Model):
    """
    Configurações de escalonamento e processamento da fila de produtos.
    Modelo singleton - deve existir apenas 1 registro.
    Editável via Django admin, sem necessidade de redeploy.
    """

    # ===== LIMITE DE FALHAS E RETRY BACKOFF =====
    limite_falhas = models.IntegerField(
        default=5,
        verbose_name="Limite de Falhas Consecutivas",
        help_text="Quantas vezes tentar antes de desativar produto (recomendado: 5). Aumento reduz falsos positivos."
    )

    retry_delay_1_minutos = models.IntegerField(
        default=5,
        verbose_name="1ª Tentativa (minutos)",
        help_text="Esperar X minutos antes de 1ª retry (recomendado: 5)"
    )

    retry_delay_2_minutos = models.IntegerField(
        default=15,
        verbose_name="2ª Tentativa (minutos)",
        help_text="Esperar X minutos antes de 2ª retry (recomendado: 15)"
    )

    retry_delay_3_minutos = models.IntegerField(
        default=60,
        verbose_name="3ª Tentativa (minutos)",
        help_text="Esperar X minutos antes de 3ª retry (recomendado: 60 = 1h)"
    )

    retry_delay_4_minutos = models.IntegerField(
        default=240,
        verbose_name="4ª Tentativa (minutos)",
        help_text="Esperar X minutos antes de 4ª retry (recomendado: 240 = 4h)"
    )

    # ===== WORKERS E FILA =====
    num_workers = models.IntegerField(
        default=2,
        verbose_name="Número de Workers",
        help_text="Threads paralelas: dev=2, staging=4, produção=8. Aumentar melhora throughput."
    )

    max_queue_size = models.IntegerField(
        default=5000,
        verbose_name="Tamanho Máximo da Fila",
        help_text="Máximo de tarefas na fila (recomendado: 5000)"
    )

    task_timeout_segundos = models.IntegerField(
        default=120,
        verbose_name="Timeout por Tarefa (segundos)",
        help_text="Tempo máximo para processar 1 produto (recomendado: 120)"
    )

    # ===== PLAYWRIGHT =====
    playwright_timeout_ms = models.IntegerField(
        default=30000,
        verbose_name="Playlist Timeout (ms)",
        help_text="Timeout para carregar página web (recomendado: 30000 = 30s)"
    )

    playwright_delay_ms = models.IntegerField(
        default=3000,
        verbose_name="Delay entre Requests (ms)",
        help_text="Esperar após abrir página (recomendado: 3000 = 3s)"
    )

    # ===== RATE LIMITING =====
    rate_limit_delay_ms = models.IntegerField(
        default=300,
        verbose_name="Rate Limit Delay (ms)",
        help_text="Esperar entre requisições (recomendado: 300ms)"
    )

    max_concurrent_requests = models.IntegerField(
        default=2,
        verbose_name="Max Requisições Paralelas",
        help_text="Quantas req simultâneas por worker (recomendado: 2)"
    )

    # ===== DATABASE =====
    use_sqlite = models.BooleanField(
        default=False,
        verbose_name="Usar SQLite (Dev Local)",
        help_text="Só para dev local. Produção: sempre MySQL/PostgreSQL"
    )

    sqlite_timeout_segundos = models.IntegerField(
        default=60,
        verbose_name="SQLite Timeout (segundos)",
        help_text="Timeout para operações SQLite (recomendado: 60)"
    )

    # ===== LOGGING =====
    log_level = models.CharField(
        max_length=20,
        choices=[
            ('DEBUG', 'Debug - Muitos detalhes'),
            ('INFO', 'Info - Informações principais'),
            ('WARNING', 'Warning - Apenas alertas'),
            ('ERROR', 'Error - Apenas erros'),
        ],
        default='INFO',
        verbose_name="Nível de Log",
        help_text="Controla verbosidade dos logs (dev=DEBUG, prod=INFO)"
    )

    logs_retention_dias = models.IntegerField(
        default=30,
        verbose_name="Retenção de Logs (dias)",
        help_text="Deletar logs com mais de X dias (recomendado: 30)"
    )

    # ===== SEGURANÇA =====
    session_timeout_minutos = models.IntegerField(
        default=30,
        verbose_name="Timeout de Logout (minutos)",
        help_text="Tempo de inatividade antes de fazer logout automático (recomendado: 30 min). "
                  "Usado em: SESSION_COOKIE_AGE no Django"
    )

    # ===== METADATA =====
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização"
    )

    nota = models.TextField(
        blank=True,
        default="",
        verbose_name="Notas / Changelog",
        help_text="Documenterenomudanças realizadas (ex: 'Aumentado retry_delay_1 de 5 para 10 -> muitos timeouts')"
    )

    class Meta:
        verbose_name = "Configuração de Escalonamento"
        verbose_name_plural = "Configuração de Escalonamento (Singleton)"

    def __str__(self):
        return f"EscalonamentoConfig (atualizado: {self.atualizado_em.strftime('%d/%m %H:%M')})"

    @classmethod
    def obter_config(cls):
        """
        Retorna a única instância da config. Cria com defaults se não existir.
        Uso: config = EscalonamentoConfig.obter_config()
        """
        config, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'limite_falhas': 5,
                'num_workers': 2,
            }
        )
        return config

    def save(self, *args, **kwargs):
        """Garante que existe apenas 1 registro (singleton)"""
        self.pk = 1  # Always use pk=1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Impede deletar a configuração"""
        raise ValueError("❌ Não é possível deletar EscalonamentoConfig. Editar ao invés disso.")


# ============================================================
# COLETA DE DADOS - Clientes para Newsletter
# ============================================================

class CanalPrefundido(models.TextChoices):
    """Canais de comunicação preferidos do cliente."""
    EMAIL = 'email', 'Email'
    WHATSAPP = 'whatsapp', 'WhatsApp'
    AMBOS = 'ambos', 'Email e WhatsApp'


class Cliente(models.Model):
    """
    Modelo para captura de contatos interessados em receber atualizações.
    Coleta dados para newsletter, promoções e análises.
    
    NÃO é usado para login - apenas para coleta de dados.
    """
    nome = models.CharField(
        max_length=150,
        verbose_name="Nome Completo",
        help_text="Nome do cliente"
    )
    email = models.EmailField(
        verbose_name="Email",
        unique=True,
        db_index=True
    )
    telefone = models.CharField(
        max_length=20,
        verbose_name="Telefone",
        help_text="Com DDD (exemplo: 11999999999)"
    )
    
    # Preferências de recebimento
    canal_preferido = models.CharField(
        max_length=20,
        choices=CanalPrefundido.choices,
        default=CanalPrefundido.EMAIL,
        verbose_name="Canal Preferido de Contato"
    )
    
    # Tipos de conteúdo de interesse
    receber_promocoes = models.BooleanField(
        default=True,
        verbose_name="Receber Promoções",
        help_text="Enviar notificações de ofertas e descontos"
    )
    receber_analises = models.BooleanField(
        default=True,
        verbose_name="Receber Análises",
        help_text="Enviar análises de produtos e comparativos"
    )
    receber_atualizacoes = models.BooleanField(
        default=True,
        verbose_name="Receber Atualizações",
        help_text="Enviar notícias e atualizações do site"
    )
    
    # Status
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Cliente ativo/inativo",
        db_index=True
    )
    
    # Metadata
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Cadastrado em",
        db_index=True
    )
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Última atualização"
    )
    
    # Rastreamento
    ip_origem = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP de Origem",
        help_text="IP do navegador ao fazer cadastro"
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User Agent",
        help_text="Informações do navegador/device"
    )
    
    # Confirmação
    confirmado = models.BooleanField(
        default=False,
        verbose_name="Email Confirmado",
        help_text="Cliente confirmou email (double-opt-in)"
    )
    token_confirmacao = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Token de Confirmação"
    )
    
    class Meta:
        verbose_name = "Cliente / Contato"
        verbose_name_plural = "Clientes / Contatos"
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['email'], name='idx_cliente_email'),
            models.Index(fields=['ativo', '-criado_em'], name='idx_cliente_ativo_data'),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.email})"


# ============================================================
# CONFIGURAÇÃO DE MANUTENÇÃO DO SITE
# ============================================================

class SiteMaintenanceConfig(models.Model):
    """
    Configuração de manutenção do site - Singleton.
    Apenas 1 registro deve existir. Editável via Django Admin.
    
    Quando ativo, o middleware intercepta requisições e exibe template de manutenção.
    """
    em_manutencao = models.BooleanField(
        default=False,
        verbose_name="Site em Manutenção",
        help_text="Marque para ativar modo de manutenção"
    )
    
    titulo = models.CharField(
        max_length=200,
        default="Sistema em Manutenção",
        verbose_name="Título",
        help_text="Título exibido no topo da página de manutenção"
    )
    
    mensagem = models.TextField(
        default="Estamos realizando uma atualização programada. Retorne em breve!",
        verbose_name="Mensagem de Manutenção",
        help_text="Mensagem detalhada exibida aos clientes (suporta HTML básico)"
    )
    
    tempo_estimado_minutos = models.IntegerField(
        default=30,
        verbose_name="Tempo Estimado de Retorno (minutos)",
        help_text="Tempo estimado para conclusão da manutenção"
    )
    
    mostrar_tempo_estimado = models.BooleanField(
        default=True,
        verbose_name="Exibir Tempo Estimado",
        help_text="Se ativo, exibe 'Tempo estimado de retorno: X min'"
    )
    
    email_contato = models.EmailField(
        blank=True,
        verbose_name="Email de Contato",
        help_text="Email para dúvidas (opcional)"
    )
    
    data_inicio = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Data/Hora de Início",
        help_text="Quando a manutenção começou"
    )
    
    criado_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Criado em"
    )
    
    atualizado_em = models.DateTimeField(
        auto_now=True,
        verbose_name="Atualizado em"
    )
    
    class Meta:
        verbose_name = "Configuração de Manutenção do Site"
        verbose_name_plural = "Configuração de Manutenção do Site"
    
    def __str__(self):
        status = "🔴 ATIVO" if self.em_manutencao else "🟢 INATIVO"
        return f"Manutenção do Site [{status}]"
    
    def save(self, *args, **kwargs):
        """Garante que apenas 1 registro existe (Singleton)."""
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Impede exclusão do registro único."""
        pass
    
    @classmethod
    def get_config(cls):
        """Obtém a configuração única do site, criando se não existir."""
        config, _ = cls.objects.get_or_create(pk=1)
        return config
