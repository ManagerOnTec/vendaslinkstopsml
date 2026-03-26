from django.db import migrations


def populate_plataformas(apps, schema_editor):
    """Popula a tabela PlataformaEcommerce."""
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
        migrations.RunPython(populate_plataformas),
    ]
