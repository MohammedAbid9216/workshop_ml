from fastapi import APIRouter, Depends
from ..auth import require_permission
router=APIRouter(prefix="/api/admin",tags=["Admin"])
@router.get("/health")
def health(user=Depends(require_permission("admin.dashboard.view"))): return {"ok":True,"role":user.role.name}
