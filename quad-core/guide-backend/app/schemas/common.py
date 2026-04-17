"""
Shared API response primitives -- warnings, errors, and validation results.
"""
from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    """Uyari onemi: INFO bilgilendirme, WARN eylem gerektirebilir."""

    INFO = "INFO"
    WARN = "WARN"


class ApiWarning(BaseModel):
    """Non-fatal uyari mesaji -- istek basarili olsa da istemciye iletilir."""

    code: str
    severity: Severity = Severity.WARN
    message: str


class ApiErrorResponse(BaseModel):
    """Hata durumlarinda donen standart hata yapisi."""

    error_code: str
    message: str
    details: list[str] = []


class ValidationResult(BaseModel):
    """RequestValidator metodlarindan donen dogrulama sonucu."""

    is_valid: bool
    errors: list[str] = []
    warnings: list[ApiWarning] = []
