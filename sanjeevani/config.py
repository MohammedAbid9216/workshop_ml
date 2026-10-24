from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sanjeevani Clinic"
    env: str = "development"
    secret_key: str = "change-this-secret"

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = ""
    db_name: str = "sanjeevani_clinic"

    access_token_minutes: int = 60
    log_dir: str = "logs/sanjeevani"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


settings = Settings()
