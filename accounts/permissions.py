"""
Role-based access control for SSBikez ERP.

Maps role names (as stored in accounts.Role.role_name) to the list of
URL namespaces (Django app namespaces) the role is allowed to access.

A '*' value grants access to every namespace.
"""

ROLE_PERMISSIONS = {
    'Managing Director': ['*'],
    'Sales Manager':     ['sales', 'customers', 'customer_vehicles', 'billing', 'rto', 'vas', 'accounts'],
    'Sales Executive':   ['sales', 'customers', 'customer_vehicles', 'accounts'],
    'Cashier':           ['billing', 'rto', 'customers', 'sales', 'vas', 'accounts'],
    'Accounts':          ['billing', 'rto', 'accounts'],
    'Spares':            ['spares', 'masters', 'accounts'],
    'CRE Telecaller':    ['service', 'customer_vehicles', 'accounts'],
    'Supervisor':        ['service', 'accounts'],
    'Floor Supervisor':  ['service', 'spares', 'accounts'],
    'Service Advisor':   ['service', 'spares', 'customer_vehicles', 'accounts'],
    'Service Billing':   ['service', 'billing', 'spares', 'accounts'],
    'Service Manager':   ['service', 'spares', 'customer_vehicles', 'accounts'],
}


# Namespaces that should never be blocked (login, logout, OTP, password reset, etc)
ALWAYS_ALLOWED_NAMESPACES = {'admin'}


def get_allowed_namespaces(user):
    """Return the list of namespaces the given user may access."""
    if not user or not user.is_authenticated:
        return []
    if user.is_superuser:
        return ['*']
    role = getattr(user, 'role', None)
    role_name = role.role_name if role else ''
    return ROLE_PERMISSIONS.get(role_name, [])


def user_can_access(user, namespace):
    """Return True if the user can access the given URL namespace."""
    allowed = get_allowed_namespaces(user)
    if '*' in allowed:
        return True
    return namespace in allowed


# ---------------------------------------------------------------------------
# Object-level (IDOR) checks
#
# Namespace checks above only gate "can this role open this app at all".
# These helpers gate "can this specific user mutate this specific record" —
# used on edit/delete views for records that carry an owner field
# (created_by / sales_executive / service_advisor / etc).
# ---------------------------------------------------------------------------

# Roles trusted to manage records they didn't personally create.
MANAGEMENT_ROLES = {
    'Managing Director', 'Sales Manager', 'Floor Supervisor',
    'Service Manager', 'Supervisor',
}

# Owner fields checked, in order, across the various models in this app.
_OWNER_FIELDS = ('created_by', 'sales_executive', 'service_advisor', 'assigned_to')


def user_is_manager(user):
    """True for superusers and roles trusted to manage everyone's records."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', None)
    return bool(role and role.role_name in MANAGEMENT_ROLES)


def user_owns(user, obj):
    """
    True if `user` may mutate `obj`.

    Managers always pass. Otherwise, true if `user` matches any populated
    owner field on `obj`. If `obj` has none of the recognised owner fields
    at all, there's no ownership concept for that model — fall back to True
    (the namespace-level role gate already covers it).
    """
    if user_is_manager(user):
        return True
    has_owner_field = False
    for field in _OWNER_FIELDS:
        if hasattr(obj, f'{field}_id'):
            has_owner_field = True
            if getattr(obj, f'{field}_id') == user.pk:
                return True
    return not has_owner_field


# ---------------------------------------------------------------------------
# Module-level Create/Read/Edit/Delete permission matrix
#
# Layered on top of the namespace-level ROLE_PERMISSIONS check above: that
# gate decides "can this role open this app at all"; ModulePermission rows
# (managed from Admin -> Module Access) narrow it further to "can this role
# Create/Edit/Delete within a specific module" — matching the reference
# ERP's per-role permission matrix (Display/Edit/Create/Delete checkboxes).
# ---------------------------------------------------------------------------

_ACTION_FIELD = {
    'view':   'can_view',
    'create': 'can_create',
    'edit':   'can_edit',
    'delete': 'can_delete',
}


def user_can_perform(user, module, action):
    """
    True if `user` may perform `action` ('view'/'create'/'edit'/'delete')
    within `module` (a ModulePermission.MODULE_CHOICES key).

    Superusers always pass. Absence of a ModulePermission row for the
    user's role + module means "allowed" (only an explicit False on the
    matching field narrows access) — consistent with can_see_module.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    role = getattr(user, 'role', None)
    if not role:
        return False

    from accounts.models import ModulePermission
    override = ModulePermission.objects.filter(role=role, module=module).first()
    if override is None:
        return True
    field = _ACTION_FIELD.get(action, 'can_view')
    return getattr(override, field, True)


def require_module_action(module, action):
    """
    View decorator: 403s unless user_can_perform(request.user, module, action).
    Use on create/update/delete views to enforce the Module Access matrix
    at the action level, beyond the namespace-level @login_required gate.
    """
    from functools import wraps
    from django.http import HttpResponseForbidden

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if not user_can_perform(request.user, module, action):
                return HttpResponseForbidden(
                    f'<h1>403 — Access Denied</h1><p>Your role does not have '
                    f'"{action}" permission for this module.</p>'
                )
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
