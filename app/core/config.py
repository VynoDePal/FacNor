from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "FacNor API"
    database_url: str = "sqlite:///./facnor.db"
    jwt_secret_key: str = "change-me-in-production-with-32-bytes-minimum"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_prefix="FACNOR_")


settings = Settings()
