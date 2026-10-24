import logging
from ..database.models import AuditLog
logger = logging.getLogger("sanjeevani.audit")

def record(db, actor_id, action, resource=None, resource_id=None, metadata=None):
    db.add(AuditLog(actor_user_id=actor_id, action=action, resource=resource, resource_id=str(resource_id) if resource_id else None, metadata_json=metadata))
    logger.info("actor=%s action=%s resource=%s resource_id=%s", actor_id, action, resource, resource_id)
