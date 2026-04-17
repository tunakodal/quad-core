"""
Shared API response primitives — warnings, errors, and validation results.
"""
from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    """API uyarılarının önem derecesi. INFO bilgilendirme, WARN eylem gerektirebilir."""

    INFO = "INFO"
    WARN = "WARN"


class ApiWarning(BaseModel):
    """
    İstek başarılı olsa da istemciye iletilmesi gereken uyarı mesajı.

    Örnek: Yeterli POI bulunamaması (PARTIAL_ITINERARY), içerik eksikliği (CONTENT_NOT_FOUND).
    """

    code: str
    severity: Severity = Severity.WARN
    message: str


class ApiErrorResponse(BaseModel):
    """
    Hata durumlarında dönen standart hata yapısı.

    error_code makine tarafından okunabilir (ör. NOT_FOUND, VALIDATION_ERROR),
    message insan tarafından okunabilir açıklamadır.
    """

    error_code: str
    message: str
    details: list[str] = []


class ValidationResult(BaseModel):
    """
    RequestValidator metodlarının döndürdüğü doğrulama sonucu.

    is_valid False ise errors listesi dolu olacaktır ve istek reddedilmelidir.
    warnings ise isteğin işlenebileceğini ama dikkat edilmesi gereken
    durumlar olduğunu belirtir.
    """

    is_valid: bool
    errors: list[str] = []
    warnings: list[ApiWarning] = []
