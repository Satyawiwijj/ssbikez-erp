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
