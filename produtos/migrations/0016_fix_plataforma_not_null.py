import django.db.models.deletion
from django.db import migrations, models


def populate_plataformas(apps, schema_editor):
    """Popula tabela pois 0015 foi fakeada e nunca rodou."""
    PlataformaEcommerce = apps.get_model('produtos', 'PlataformaEcommerce')
    
    plataformas = [
        {'chave': 'mercado_livre', 'nome': 'Mercado Livre', 'ordem': 0},
        {'chave': 'amazon', 'nome': 'Amazon', 'ordem': 1},
        {'chave': 'shopee', 'nome': 'Shopee', 'ordem': 2},
        {'chave': 'shein', 'nome': 'Shein', 'ordem': 3},
        {'chave': 'outro', 'nome': 'Outro', 'ordem': 4},
    ]
    
    for plat in plataformas:
        PlataformaEcommerce.objects.get_or_create(**plat)


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0015_plataformaecommerce_and_more'),
    ]

    operations = [
        # Populate - 0015 foi fakeada então isso não rodou
        migrations.RunPython(populate_plataformas),
        # ALTER para nullable
        migrations.AlterField(
            model_name='produtoautomatico',
            name='plataforma',
            field=models.ForeignKey(blank=True, help_text='Detectada automaticamente pela URL do link', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos', to='produtos.plataformaecommerce', verbose_name='Plataforma'),
        ),
    ]

