from .models import AuditLog


def log_action(user, action, entity_type, entity_id, entity_str='', details=''):
    AuditLog.objects.create(
        user=user,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        entity_str=str(entity_str)[:200],
        details=details,
    )
