import os
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".env"
    ),
    override=False,
)


def get_db_connection():
    host = os.getenv("DB_HOST", "127.0.0.1")
    connection_args = {
        "host": host,
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "database": os.getenv("DB_NAME", "defaultdb"),
        "connection_timeout": 10,
    }

    if host not in ("localhost", "127.0.0.1"):
        ca_path = os.getenv(
            "DB_SSL_CA",
            str(Path(__file__).resolve().parents[1] / "certs" / "ca.pem"),
        )
        if not os.path.isfile(ca_path):
            raise RuntimeError(f"MySQL CA certificate not found: {ca_path}")

        connection_args.update({
            "ssl_ca": ca_path,
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        })

    return mysql.connector.connect(**connection_args)
