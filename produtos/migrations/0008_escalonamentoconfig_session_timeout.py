# Generated migration - Adiciona campo de timeout de logout

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0007_merge_20260323_2324'),
    ]

    operations = [
        migrations.AddField(
            model_name='escalonamentoconfig',
            name='session_timeout_minutos',
            field=models.IntegerField(
                default=30,
                verbose_name='Timeout de Logout (minutos)',
                help_text='Tempo de inatividade antes de fazer logout automático (recomendado: 30 min). '
                          'Usado em: SESSION_COOKIE_AGE no Django'
            ),
        ),
    ]
