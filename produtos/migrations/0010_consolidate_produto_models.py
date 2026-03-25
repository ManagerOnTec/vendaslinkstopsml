# Generated migration for consolidating Produto and ProdutoAutomatico into single model

from django.db import migrations, models


def migrate_produto_to_automatic(apps, schema_editor):
    """
    Migra dados da tabela Produto antiga para ProdutoAutomatico.
    Se houver registros em Produto, cria correspondentes em ProdutoAutomatico com origem=MANUAL.
    """
    try:
        Produto = apps.get_model('produtos', 'Produto')
        ProdutoAutomatico = apps.get_model('produtos', 'ProdutoAutomatico')
        
        for produto in Produto.objects.all():
            # Criar correspondente em ProdutoAutomatico com origem MANUAL
            ProdutoAutomatico.objects.get_or_create(
                pk=produto.pk,
                defaults={
                    'origem': 'manual',
                    'titulo': produto.titulo,
                    'imagem_url': produto.imagem_url,
                    'imagem': produto.imagem,
                    'link_afiliado': produto.link_afiliado,
                    'preco': produto.preco,
                    'preco_original': produto.preco_original,
                    'categoria': produto.categoria,
                    'destaque': produto.destaque,
                    'ativo': produto.ativo,
                    'ordem': produto.ordem,
                    'criado_em': produto.criado_em,
                    'atualizado_em': produto.atualizado_em,
                    'plataforma': 'outro',
                    'status_extracao': 'sucesso',
                }
            )
    except Exception as e:
        print(f"Alerta: Não foi possível migrar dados de Produto: {e}")


def reverse_migrate(apps, schema_editor):
    """Reverter é seguro - apenas remove origem."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('produtos', '0009_remove_produtoautomatico_idx_status_extracao_and_more'),
    ]

    operations = [
        # Adiciona campo origem ao ProdutoAutomatico
        migrations.AddField(
            model_name='produtoautomatico',
            name='origem',
            field=models.CharField(
                choices=[('automatico', 'Extraído Automaticamente'), ('manual', 'Criado Manualmente')],
                db_index=True,
                default='automatico',
                help_text='Indica se foi extraído automaticamente ou criado manualmente',
                max_length=20,
                verbose_name='Origem'
            ),
        ),
        
        # Migra dados de Produto para ProdutoAutomatico (se houver)
        migrations.RunPython(migrate_produto_to_automatic, reverse_migrate),
        
        # Deleta modelo Produto (e sua tabela)
        migrations.DeleteModel(
            name='Produto',
        ),
    ]
