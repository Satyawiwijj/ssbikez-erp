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


@register.simple_tag(takes_context=True)
def can_see_module(context, module_key, *allowed_roles):
    """
    Same role check as can_see_section, with an additional per-module
    override: if a ModulePermission row exists for the user's role and
    module_key, its can_view value wins (lets an admin hide a module for
    a role that would otherwise see it). No row means "use the role default".
    Superusers always see everything, regardless of overrides.
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
    if not role_name or role_name not in allowed_roles:
        return False

    from accounts.models import ModulePermission
    override = ModulePermission.objects.filter(role=role, module=module_key).first()
    if override is not None:
        return override.can_view
    return True


@register.simple_tag(takes_context=True)
def can_access_ns(context, namespace):
    """
    True if the current user may access the given URL namespace, per the
    same accounts.permissions.ROLE_PERMISSIONS table the URL-level RBAC
    decorator enforces. Use this to hide action buttons/links a user would
    otherwise click into a 403 — it can't drift from the real enforcement
    logic the way a hardcoded role list in a template would.
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False
    from accounts.permissions import user_can_access
    return user_can_access(request.user, namespace)
