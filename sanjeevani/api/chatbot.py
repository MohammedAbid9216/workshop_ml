from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User
from ..chatbot.engine import chatbot_response


router = APIRouter(
    prefix="/api/chatbot",
    tags=["Chatbot"],
)


class ChatMessage(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=2000,
    )


@router.post("/message")
def send_message(
    data: ChatMessage,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(
            status_code=403,
            detail="Chatbot is available for patients",
        )

    if not user.patient:
        raise HTTPException(
            status_code=400,
            detail="Patient profile not found",
        )

    response = chatbot_response(
        text=data.message,
        patient_id=user.patient.id,
        db=db,
    )

    return {
        "success": True,
        "response": response,
    }
