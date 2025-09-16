# templates/templatetags/form_extras.py
from django import template

register = template.Library()

@register.filter
def add_class(field, css):
    """Append Tailwind classes to a form field widget."""
    attrs = field.field.widget.attrs
    existing = attrs.get("class", "")
    attrs["class"] = (existing + " " + css).strip()
    return field.as_widget(attrs=attrs)
