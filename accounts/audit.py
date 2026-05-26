"""
Audit logging helper — call log_action() in any view to record an audit trail.
Never raises exceptions — audit failures must not crash user-facing requests.
"""
from .models import AuditLog


def log_action(request, module_name, action_name, record_id=None):
    """
    Create an AuditLog entry.

    :param request:     Django HttpRequest
    :param module_name: e.g. 'Customer', 'Job Card', 'Invoice'
    :param action_name: one of AuditLog.Action choices: 'create', 'update', 'delete', 'view'
    :param record_id:   PK of the affected object (optional)
    """
    try:
        user = (
            request.user
            if hasattr(request, 'user') and request.user.is_authenticated
            else None
        )
        AuditLog.objects.create(
            user=user,
            module_name=module_name,
            action_name=action_name,
            record_id=record_id,
            ip_address=request.META.get('REMOTE_ADDR'),
        )
    except Exception:
        pass  # Never let audit logging crash a request
