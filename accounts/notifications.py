"""
Notification helpers.

generate_notifications(user) — scans business data and creates Notification
records for the given user (or all staff if user is None).

Call this from a context processor or management command.
Never raises exceptions.
"""
from django.utils import timezone


def generate_notifications(user):
    """
    Generate system notifications for `user`.
    Returns a queryset of unread Notification objects for that user.
    """
    try:
        from .models import Notification

        # 1. Low-stock spares
        try:
            from spares.models import SparesItem, StockLedger
            from django.db.models import Sum, F, ExpressionWrapper, DecimalField

            items = SparesItem.objects.filter(maintain_stock=True, is_active=True)
            for item in items:
                total_in  = StockLedger.objects.filter(item=item, entry_type='in').aggregate(
                    t=Sum('quantity'))['t'] or 0
                total_out = StockLedger.objects.filter(item=item, entry_type='out').aggregate(
                    t=Sum('quantity'))['t'] or 0
                stock = total_in - total_out
                if item.reorder_level and stock <= item.reorder_level:
                    key = f'low_stock_{item.pk}'
                    if not Notification.objects.filter(
                        user=user, title__startswith='Low Stock', message__contains=item.item_name,
                        is_read=False,
                        created_at__date=timezone.now().date(),
                    ).exists():
                        Notification.objects.create(
                            user=user,
                            title='Low Stock Alert',
                            message=f'{item.item_name} (code: {item.item_code}) is at {stock} units — reorder level is {item.reorder_level}.',
                            level=Notification.Level.WARNING,
                            link='/spares/stock/',
                        )
        except Exception:
            pass

        # 2. Insurance expiry within 30 days
        try:
            from customer_vehicles.models import CustomerVehicle
            cutoff = timezone.now().date() + timezone.timedelta(days=30)
            expiring = CustomerVehicle.objects.filter(
                insurance_expiry__lte=cutoff,
                insurance_expiry__gte=timezone.now().date(),
            ).select_related('vehicle__bike_model', 'customer')
            for cv in expiring:
                if not Notification.objects.filter(
                    user=user,
                    title='Insurance Expiry',
                    message__contains=cv.registration_no or str(cv.pk),
                    is_read=False,
                    created_at__date=timezone.now().date(),
                ).exists():
                    Notification.objects.create(
                        user=user,
                        title='Insurance Expiry',
                        message=f'Vehicle {cv.registration_no or cv.vehicle.bike_model} for {cv.customer.full_name} expires on {cv.insurance_expiry}.',
                        level=Notification.Level.WARNING,
                        link='/accounts/insurance-expiry/',
                    )
        except Exception:
            pass

    except Exception:
        pass


def get_unread_count(user):
    """Return unread notification count for a user."""
    try:
        from .models import Notification
        return Notification.objects.filter(user=user, is_read=False).count()
    except Exception:
        return 0
