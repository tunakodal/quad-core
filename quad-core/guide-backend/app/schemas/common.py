"""
Shared API response primitives — warnings, errors, and validation results.
"""
from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"


class ApiWarning(BaseModel):
    code: str
    severity: Severity = Severity.WARN
    message: str


class ApiErrorResponse(BaseModel):
    error_code: str
    message: str
    details: list[str] = []


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[ApiWarning] = []
