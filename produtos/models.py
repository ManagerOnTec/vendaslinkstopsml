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


class Produto(models.Model):
    """Produto com link afiliado do Mercado Livre."""
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título",
        help_text="Nome do produto exibido no site"
    )
    imagem_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name="URL da Imagem",
        help_text="Link externo da imagem do produto"
    )
    imagem = models.ImageField(
        upload_to='produtos/%Y/%m/',
        blank=True,
        null=True,
        verbose_name="Imagem (Upload)",
        help_text="Ou faça upload de uma imagem local"
    )
    link_afiliado = models.URLField(
        max_length=500,
        verbose_name="Link Afiliado",
        help_text="Link de afiliado do Mercado Livre"
    )
    preco = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Preço",
        help_text="Ex: R$ 99,90 ou 'A partir de R$ 49,90'"
    )
    preco_original = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Preço Original",
        help_text="Preço antes do desconto (riscado). Ex: R$ 149,90"
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produtos',
        verbose_name="Categoria"
    )
    destaque = models.BooleanField(
        default=False,
        verbose_name="Destaque",
        help_text="Produtos em destaque aparecem primeiro"
    )
    ativo = models.BooleanField(
        default=True,
        verbose_name="Ativo",
        help_text="Apenas produtos ativos são exibidos no site"
    )
    ordem = models.IntegerField(
        default=0,
        verbose_name="Ordem",
        help_text="Ordem de exibição (menor = primeiro)"
    )
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ['-destaque', 'ordem', '-criado_em']

    def get_imagem(self):
        """Retorna a URL da imagem (upload ou URL externa)."""
        if self.imagem and hasattr(self.imagem, 'url'):
            return self.imagem.url
        elif self.imagem_url:
            return self.imagem_url
        return '/static/images/no-image.png'

    def __str__(self):
        return self.titulo


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


class StatusExtracao(models.TextChoices):
    PENDENTE = 'pendente', 'Pendente'
    PROCESSANDO = 'processando', 'Processando...'
    SUCESSO = 'sucesso', 'Extraído com Sucesso'
    ERRO = 'erro', 'Erro na Extração'


class ProdutoAutomatico(models.Model):
    """Produto com dados extraídos automaticamente do Mercado Livre.
    O utilizador cadastra apenas o link afiliado e o sistema extrai
    título, imagem, preço e descrição automaticamente."""
    link_afiliado = models.URLField(
        max_length=500,
        verbose_name="Link Afiliado",
        help_text="Cole aqui o link do produto do Mercado Livre (ex: https://mercadolivre.com.br/... ou https://meli.la/...)"
    )
    # Campos extraídos automaticamente
    titulo = models.CharField(
        max_length=500,
        blank=True,
        verbose_name="Título",
        help_text="Extraído automaticamente do Mercado Livre"
    )
    imagem_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="URL da Imagem",
        help_text="Extraída automaticamente do Mercado Livre"
    )
    preco = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Preço",
        help_text="Extraído automaticamente do Mercado Livre"
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
        help_text="Extraída automaticamente do Mercado Livre"
    )
    url_final = models.URLField(
        max_length=500,
        blank=True,
        verbose_name="URL Final do Produto",
        help_text="URL real do produto após redirecionamentos"
    )
    # Campos de controle
    status_extracao = models.CharField(
        max_length=20,
        choices=StatusExtracao.choices,
        default=StatusExtracao.PENDENTE,
        verbose_name="Status da Extração"
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
        verbose_name="Ativo"
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
        verbose_name="Última Extração"
    )
    falhas_consecutivas = models.IntegerField(
        default=0,
        verbose_name="Falhas Consecutivas",
        help_text="Número de tentativas de atualização que falharam. Ao atingir limite, produto é desativado automaticamente."
    )
    motivo_desativacao = models.TextField(
        blank=True,
        verbose_name="Motivo da Desativação",
        help_text="Registra o motivo automático de desativação (ex: 5 falhas consecutivas)"
    )

    class Meta:
        verbose_name = "Produto Automático"
        verbose_name_plural = "Produtos Automáticos"
        ordering = ['-destaque', 'ordem', '-criado_em']

    def get_imagem(self):
        """Retorna a URL da imagem extraída."""
        return self.imagem_url or '/static/images/no-image.png'

    def __str__(self):
        return self.titulo or f"Produto (link: {self.link_afiliado[:50]}...)"


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
