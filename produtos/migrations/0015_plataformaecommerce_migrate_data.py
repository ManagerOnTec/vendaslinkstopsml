# Generated manually to handle PlataformaEcommerce migration with data

from django.db import migrations, models
import django.db.models.deletion


def populate_plataformas(apps, schema_editor):
    """Popula a tabela PlataformaEcommerce com os valores das plataformas."""
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


def migrate_produtos_plataforma(apps, schema_editor):
    """Migra os valores do campo CharField para a FK."""
    ProdutoAutomatico = apps.get_model('produtos', 'ProdutoAutomatico')
    PlataformaEcommerce = apps.get_model('produtos', 'PlataformaEcommerce')
    
    # Para cada produto com plataforma CharField, atribua a FK correspondente
    for produto in ProdutoAutomatico.objects.all():
        if produto.plataforma_id and isinstance(produto.plataforma_id, str):
            try:
                plt = PlataformaEcommerce.objects.get(chave=produto.plataforma_id)
                produto.plataforma = plt
                produto.save()
            except PlataformaEcommerce.DoesNotExist:
                pass


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0014_create_site_maintenance_config'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlataformaEcommerce',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chave', models.CharField(help_text='Identificador único (mercado_livre, amazon, shopee, shein, outro)', max_length=20, unique=True, verbose_name='Chave')),
                ('nome', models.CharField(help_text='Nome exibido da plataforma', max_length=100, verbose_name='Nome')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('ordem', models.IntegerField(default=0, help_text='Ordem de exibição nos filtros', verbose_name='Ordem')),
                ('criado_em', models.DateTimeField(auto_now_add=True, verbose_name='Criado em')),
            ],
            options={
                'verbose_name': 'Plataforma E-commerce',
                'verbose_name_plural': 'Plataformas E-commerce',
                'ordering': ['ordem', 'nome'],
            },
        ),
        migrations.RunPython(populate_plataformas),
        migrations.AlterField(
            model_name='produtoautomatico',
            name='plataforma',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='produtos', to='produtos.plataformaecommerce', verbose_name='Plataforma', help_text='Detectada automaticamente pela URL do link'),
        ),
        migrations.RunPython(migrate_produtos_plataforma),
    ]
