"""
Role-based access middleware.

Restricts access to URL namespaces based on the logged-in user's role.
"""
from django.http import HttpResponseForbidden
from django.template.loader import render_to_string


# URL paths (or path prefixes) that are always allowed regardless of role
_PUBLIC_PATHS = (
    '/accounts/login/',
    '/accounts/logout/',
    '/accounts/verify-otp/',
    '/accounts/password/',
    '/accounts/profile/',
    '/accounts/profile/edit/',
    '/accounts/home/',
    '/accounts/dashboard/',
    '/accounts/search/',
)


class RolePermissionMiddleware:
    """Block access to apps the current user's role isn't permitted to use."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip unauthenticated requests (login view handles it)
        if not request.user.is_authenticated:
            return None
        if request.user.is_superuser:
            return None

        # Always allow common account-level URLs
        path = request.path or ''
        for prefix in _PUBLIC_PATHS:
            if path.startswith(prefix):
                return None

        # Resolve URL namespace
        match = request.resolver_match
        if not match:
            return None
        namespace = match.namespace or ''

        # Allow admin & no-namespace (root) requests
        if not namespace or namespace == 'admin':
            return None

        from accounts.permissions import ROLE_PERMISSIONS

        role = getattr(request.user, 'role', None)
        role_name = role.role_name if role else ''
        allowed = ROLE_PERMISSIONS.get(role_name, [])

        if '*' in allowed:
            return None
        if namespace in allowed:
            return None

        # Block — render branded 403
        try:
            html = render_to_string('403.html', {
                'namespace': namespace,
                'role_name': role_name or 'No Role',
            }, request=request)
        except Exception:
            html = '<h1>403 — Access Denied</h1>'
        return HttpResponseForbidden(html)
