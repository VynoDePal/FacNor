from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from backend.app.models.client import ClientType

COMPANY_IDENTITY_REQUIRED_MESSAGE = "Un client Entreprise doit renseigner un SIREN ou un numéro de TVA"
SIREN_DIGITS_MESSAGE = "Le SIREN doit contenir exactement 9 chiffres"


def normalize_optional_identifier(value: str | None) -> str | None:
    if isinstance(value, str) and not value.strip():
        return None
    return value


def validate_siren_digits(value: str | None) -> str | None:
    if value is not None and not value.isdigit():
        raise ValueError(SIREN_DIGITS_MESSAGE)
    return value


def validate_company_identity(
    client_type: ClientType | None,
    siren: str | None,
    vat_number: str | None,
) -> None:
    if client_type == ClientType.ENTREPRISE and not (siren or vat_number):
        raise ValueError(COMPANY_IDENTITY_REQUIRED_MESSAGE)


class ClientIdentityValidationMixin(BaseModel):
    @field_validator("siren", "vat_number", mode="before", check_fields=False)
    @classmethod
    def empty_string_to_none(cls, value: str | None) -> str | None:
        return normalize_optional_identifier(value)

    @field_validator("siren", check_fields=False)
    @classmethod
    def siren_must_contain_nine_digits(cls, value: str | None) -> str | None:
        return validate_siren_digits(value)


class ClientOptionalData(ClientIdentityValidationMixin):
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    address: str | None = None
    siren: str | None = Field(default=None, min_length=9, max_length=9)
    vat_number: str | None = Field(default=None, max_length=32)


class ClientBase(ClientOptionalData):
    type: ClientType
    name: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def company_requires_siren_or_vat(self) -> "ClientBase":
        validate_company_identity(self.type, self.siren, self.vat_number)
        return self


class ClientCreate(ClientBase):
    pass


class ClientUpdate(ClientOptionalData):
    type: ClientType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)


class ClientRead(ClientBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
