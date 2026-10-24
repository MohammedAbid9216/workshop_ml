
import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv(
    dotenv_path=os.path.join(
        os.path.dirname(os.path.dirname(__file__)), ".env"
    ),
    override=False,
)


def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "sanjeevani_clinic_new"),
        connection_timeout=5,
    )
