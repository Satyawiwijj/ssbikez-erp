"""
Template context processors for accounts app.

Exposes:
  - allowed_apps: list of URL namespaces the current user may access
  - company:      the singleton CompanySettings instance
"""


def user_permissions(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'allowed_apps': []}
    if request.user.is_superuser:
        return {'allowed_apps': ['*']}
    from accounts.permissions import ROLE_PERMISSIONS
    role = getattr(request.user, 'role', None)
    role_name = role.role_name if role else ''
    return {'allowed_apps': ROLE_PERMISSIONS.get(role_name, [])}


def company_context(request):
    try:
        from accounts.models import CompanySettings
        return {'company': CompanySettings.get_instance()}
    except Exception:
        return {'company': None}
