from django import template

register = template.Library()


@register.filter
def modulo(value, arg):
    """Verifica se value é divisível por arg (para inserir anúncios)."""
    try:
        return int(value) % int(arg) == 0
    except (ValueError, ZeroDivisionError):
        return False


@register.filter
def add_num(value, arg):
    """Soma dois números."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def plataforma_chave(produto):
    """
    Retorna a chave da plataforma de forma segura.
    Retorna 'outro' se plataforma for None.
    """
    if not produto or not hasattr(produto, 'plataforma'):
        return 'outro'
    if not produto.plataforma:
        return 'outro'
    return getattr(produto.plataforma, 'chave', 'outro')


@register.filter
def plataforma_nome(produto, default='Ver na Loja'):
    """
    Retorna o nome da plataforma de forma segura.
    Retorna um texto padrão se plataforma for None.
    """
    if not produto or not hasattr(produto, 'plataforma'):
        return default
    if not produto.plataforma:
        return default
    return getattr(produto.plataforma, 'nome', default)


@register.filter
def plataforma_label_botao(produto):
    """
    Retorna o label do botão adaptado à plataforma.
    Exemplo: 'Ver na Amazon', 'Ver na Shopee', etc.
    Seguro contra None.
    """
    if not produto or not hasattr(produto, 'plataforma'):
        return 'Ver na Loja'
    if not produto.plataforma:
        return 'Ver na Loja'
    
    chave = getattr(produto.plataforma, 'chave', 'outro')
    nome = getattr(produto.plataforma, 'nome', 'Loja')
    
    # Ajuste de preposição por plataforma
    prep_map = {
        'mercado_livre': 'no',
        'amazon': 'na',
        'shopee': 'na',
        'shein': 'na',
        'outro': 'na',
    }
    preposicao = prep_map.get(chave, 'na')
    
    return f'Ver {preposicao} {nome}'
