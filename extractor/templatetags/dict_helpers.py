from django import template

register = template.Library()

@register.filter(name='is_dict')
def is_dict(value):
    """
    Checks if a value is an instance of a dict.
    """
    return isinstance(value, dict)

@register.filter(name='is_list')
def is_list(value):
    """
    Checks if a value is an instance of a list.
    """
    return isinstance(value, list)

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Returns the value for a given key from a dictionary.
    Usage: {{ my_dict|get_item:"my_key" }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
