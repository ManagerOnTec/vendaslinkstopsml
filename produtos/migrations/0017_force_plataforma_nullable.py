import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0015_plataformaecommerce_and_more'),
    ]

    operations = [
        # FORCE: Alterar coluna para nullable mesmo que 0016 não tenha rodado
        migrations.AlterField(
            model_name='produtoautomatico',
            name='plataforma',
            field=models.ForeignKey(
                blank=True,
                help_text='Detectada automaticamente pela URL do link',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='produtos',
                to='produtos.plataformaecommerce',
                verbose_name='Plataforma'
            ),
        ),
    ]
