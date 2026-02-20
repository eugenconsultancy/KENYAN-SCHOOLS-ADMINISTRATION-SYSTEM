from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def get_attr(obj, attr):
    """Get an attribute from an object"""
    try:
        return getattr(obj, attr, None)
    except (TypeError, AttributeError):
        return None

@register.filter
def in_list(value, arg):
    """Check if a value is in a list"""
    return value in arg.split(',')

@register.simple_tag
def define(val=None):
    """Define a variable in template"""
    return val
