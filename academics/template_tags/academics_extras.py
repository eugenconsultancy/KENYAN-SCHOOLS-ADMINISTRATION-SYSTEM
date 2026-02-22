from django import template

register = template.Library()

@register.filter
def split(value, delimiter):
    """Split a string by delimiter and return a list"""
    if not value:
        return []
    return value.split(delimiter)

@register.filter
def get_range(value):
    """Return a range of numbers from 1 to value"""
    if not value:
        return []
    return range(1, value + 1)

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using the key"""
    try:
        return dictionary.get(key)
    except (AttributeError, TypeError):
        return None

@register.filter
def multiply(value, arg):
    """Multiply value by argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def subtract(value, arg):
    """Subtract argument from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divide value by argument"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage(value, arg):
    """Calculate percentage (value / arg * 100)"""
    try:
        if float(arg) == 0:
            return 0
        return (float(value) / float(arg)) * 100
    except (ValueError, TypeError):
        return 0

@register.simple_tag
def define(val=None):
    """Define a variable in template"""
    return val

@register.simple_tag
def query_transform(request, **kwargs):
    """Transform query parameters for pagination"""
    updated = request.GET.copy()
    for key, value in kwargs.items():
        if value is not None:
            updated[key] = value
        else:
            updated.pop(key, 0)
    return updated.urlencode()
