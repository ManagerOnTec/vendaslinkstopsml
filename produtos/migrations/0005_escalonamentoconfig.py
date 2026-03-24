# Generated migration - Adiciona modelo EscalonamentoConfig

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0004_performance_indices'),
    ]

    operations = [
        migrations.CreateModel(
            name='EscalonamentoConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('limite_falhas', models.IntegerField(default=5, help_text='Quantas vezes tentar antes de desativar produto (recomendado: 5). Aumento reduz falsos positivos.', verbose_name='Limite de Falhas Consecutivas')),
                ('retry_delay_1_minutos', models.IntegerField(default=5, help_text='Esperar X minutos antes de 1ª retry (recomendado: 5)', verbose_name='1ª Tentativa (minutos)')),
                ('retry_delay_2_minutos', models.IntegerField(default=15, help_text='Esperar X minutos antes de 2ª retry (recomendado: 15)', verbose_name='2ª Tentativa (minutos)')),
                ('retry_delay_3_minutos', models.IntegerField(default=60, help_text='Esperar X minutos antes de 3ª retry (recomendado: 60 = 1h)', verbose_name='3ª Tentativa (minutos)')),
                ('retry_delay_4_minutos', models.IntegerField(default=240, help_text='Esperar X minutos antes de 4ª retry (recomendado: 240 = 4h)', verbose_name='4ª Tentativa (minutos)')),
                ('num_workers', models.IntegerField(default=2, help_text='Threads paralelas: dev=2, staging=4, produção=8. Aumentar melhora throughput.', verbose_name='Número de Workers')),
                ('max_queue_size', models.IntegerField(default=5000, help_text='Máximo de tarefas na fila (recomendado: 5000)', verbose_name='Tamanho Máximo da Fila')),
                ('task_timeout_segundos', models.IntegerField(default=120, help_text='Tempo máximo para processar 1 produto (recomendado: 120)', verbose_name='Timeout por Tarefa (segundos)')),
                ('playwright_timeout_ms', models.IntegerField(default=30000, help_text='Timeout para carregar página web (recomendado: 30000 = 30s)', verbose_name='Playlist Timeout (ms)')),
                ('playwright_delay_ms', models.IntegerField(default=3000, help_text='Esperar após abrir página (recomendado: 3000 = 3s)', verbose_name='Delay entre Requests (ms)')),
                ('rate_limit_delay_ms', models.IntegerField(default=300, help_text='Esperar entre requisições (recomendado: 300ms)', verbose_name='Rate Limit Delay (ms)')),
                ('max_concurrent_requests', models.IntegerField(default=2, help_text='Quantas req simultâneas por worker (recomendado: 2)', verbose_name='Max Requisições Paralelas')),
                ('use_sqlite', models.BooleanField(default=False, help_text='Só para dev local. Produção: sempre MySQL/PostgreSQL', verbose_name='Usar SQLite (Dev Local)')),
                ('sqlite_timeout_segundos', models.IntegerField(default=60, help_text='Timeout para operações SQLite (recomendado: 60)', verbose_name='SQLite Timeout (segundos)')),
                ('log_level', models.CharField(choices=[('DEBUG', 'Debug - Muitos detalhes'), ('INFO', 'Info - Informações principais'), ('WARNING', 'Warning - Apenas alertas'), ('ERROR', 'Error - Apenas erros')], default='INFO', help_text='Controla verbosidade dos logs (dev=DEBUG, prod=INFO)', max_length=20, verbose_name='Nível de Log')),
                ('logs_retention_dias', models.IntegerField(default=30, help_text='Deletar logs com mais de X dias (recomendado: 30)', verbose_name='Retenção de Logs (dias)')),
                ('atualizado_em', models.DateTimeField(auto_now=True, verbose_name='Última atualização')),
                ('nota', models.TextField(blank=True, default='', help_text='Documenterenomudanças realizadas (ex: \'Aumentado retry_delay_1 de 5 para 10 -> muitos timeouts\')', verbose_name='Notas / Changelog')),
            ],
            options={
                'verbose_name': 'Configuração de Escalonamento',
                'verbose_name_plural': 'Configuração de Escalonamento (Singleton)',
            },
        ),
    ]
