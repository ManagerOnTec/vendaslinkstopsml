# Generated migration - Adiciona índices de performance

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0003_agendamentoatualizacao_logatualizacao'),
    ]

    operations = [
        # Índices simples em campos críticos
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['status_extracao'],
                name='idx_status_extracao',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['ativo'],
                name='idx_ativo',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['ultima_extracao'],
                name='idx_ultima_extracao',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['falhas_consecutivas'],
                name='idx_falhas_consecutivas',
            ),
        ),
        
        # Índices compostos para queries comuns
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['ativo', 'status_extracao'],
                name='idx_ativo_status_extracao',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['ultima_extracao', 'ativo'],
                name='idx_ultima_extracao_ativo',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['falhas_consecutivas', 'ativo'],
                name='idx_falhas_consecutivas_ativo',
            ),
        ),
        migrations.AddIndex(
            model_name='produtoautomatico',
            index=models.Index(
                fields=['plataforma', 'ativo'],
                name='idx_plataforma_ativo',
            ),
        ),
    ]
