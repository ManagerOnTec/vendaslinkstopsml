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
