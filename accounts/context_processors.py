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


def low_stock_alert(request):
    """
    Injects `low_stock_count` (int) into every template context.
    Counts SparesItems where current stock <= reorder_level.
    """
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {'low_stock_count': 0}
    try:
        from django.db.models import Sum
        from spares.models import SparesItem, StockLedger

        count = 0
        items = SparesItem.objects.filter(
            maintain_stock=True, is_active=True
        ).exclude(reorder_level=0)
        for item in items:
            total_in  = StockLedger.objects.filter(item=item, entry_type='in').aggregate(
                t=Sum('quantity'))['t'] or 0
            total_out = StockLedger.objects.filter(item=item, entry_type='out').aggregate(
                t=Sum('quantity'))['t'] or 0
            if (total_in - total_out) <= item.reorder_level:
                count += 1
        return {'low_stock_count': count}
    except Exception:
        return {'low_stock_count': 0}
