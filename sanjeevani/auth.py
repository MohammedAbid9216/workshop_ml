from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database.connection import get_db
from .database.models import User


pwd = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

bearer = HTTPBearer()


def hash_password(value):
    return pwd.hash(value)


def verify_password(value, hashed):
    return pwd.verify(value, hashed)


def create_token(user_id):
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_minutes
    )

    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": exp,
        },
        settings.secret_key,
        algorithm="HS256",
    )


def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=["HS256"],
        )

        uid = int(payload["sub"])

    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = db.get(User, uid)

    if not user or not user.active:
        raise HTTPException(
            status_code=401,
            detail="User inactive or not found",
        )

    return user


def require_permission(code):
    def checker(
        user: User = Depends(current_user),
    ):
        if user.role.name == "super_admin":
            return user

        if not any(
            rp.permission.code == code
            for rp in user.role.permissions
        ):
            raise HTTPException(
                status_code=403,
                detail="Permission denied",
            )

        return user

    return checker
