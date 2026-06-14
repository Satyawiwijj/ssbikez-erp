from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def can_see_section(context, *allowed_roles):
    """
    Returns True if the current user should see a sidebar section.
    Superusers always see everything.
    Non-superusers must have a role whose role_name EXACTLY matches
    one of the allowed_roles arguments.
    Null role or missing role_name denies access (safe default).
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    if request.user.is_superuser:
        return True
    role = getattr(request.user, 'role', None)
    if not role:
        return False
    role_name = getattr(role, 'role_name', None)
    if not role_name:
        return False
    return role_name in allowed_roles
