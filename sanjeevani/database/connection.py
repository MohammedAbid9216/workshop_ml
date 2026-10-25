import mysql.connector

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..config import settings


def get_mysql_connection():
    import os
    from pathlib import Path

    host = settings.db_host
    connection_args = {
        "host": host,
        "port": settings.db_port,
        "user": settings.db_user,
        "password": settings.db_password,
        "database": settings.db_name,
    }

    if host not in ("localhost", "127.0.0.1"):
        ca_path = os.getenv(
            "DB_SSL_CA",
            str(Path(__file__).resolve().parents[2] / "certs" / "ca.pem"),
        )
        if not os.path.isfile(ca_path):
            raise RuntimeError(f"MySQL CA certificate not found: {ca_path}")

        connection_args.update({
            "ssl_ca": ca_path,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        })

    return mysql.connector.connect(**connection_args)


engine = create_engine(
    "mysql+mysqlconnector://",
    creator=get_mysql_connection,
    pool_pre_ping=True,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

