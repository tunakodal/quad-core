"""
Shared API response primitives — warnings, errors, and validation results.
"""
from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    """Uyari onemi: INFO bilgilendirme amacli, WARN istemci tarafinda eylem gerektirebilir."""
    INFO = "INFO"
    WARN = "WARN"


class ApiWarning(BaseModel):
    """Basarili bir API yanitinin yaninda donen kritik olmayan uyari mesaji."""
    code: str
    severity: Severity = Severity.WARN
    message: str


class ApiErrorResponse(BaseModel):
    """Hata durumlarinda donen standart hata yapisi."""
    error_code: str
    message: str
    details: list[str] = []


class ValidationResult(BaseModel):
    """Istek dogrulama sonucu: hatalar ve kritik olmayan uyarilari icerir."""
    is_valid: bool
    errors: list[str] = []
    warnings: list[ApiWarning] = []
