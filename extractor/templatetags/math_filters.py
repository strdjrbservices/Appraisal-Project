from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the arg and the value"""
    return value * arg