from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "FacNor API"
    SECRET_KEY: str = "super-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = "sqlite:///./facnor.db"
    COMPANY_NAME: str = "FacNor SAS"
    COMPANY_ADDRESS: str = "123 Rue de la Facture, 75001 Paris, France"
    COMPANY_SIREN: str = "123 456 789 00012"
    COMPANY_VAT: str = "FR123456789"
    COMPANY_EMAIL: str = "contact@facnor.fr"
    COMPANY_PHONE: str = "01 23 45 67 89"


    model_config = {
        "env_file": ".env"
    }

settings = Settings()
