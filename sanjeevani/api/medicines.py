from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import current_user
from ..database.connection import get_db
from ..database.models import Medicine, User
router=APIRouter(prefix="/api/medicines",tags=["Medicines"])
@router.get("")
def medicines(user:User=Depends(current_user),db:Session=Depends(get_db)):
    return [{"id":m.id,"name":m.name,"generic_name":m.generic_name,"price":str(m.unit_price),"stock":m.stock_qty} for m in db.query(Medicine).filter(Medicine.active==True).all()]
