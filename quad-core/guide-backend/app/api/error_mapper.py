from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.schemas.dtos import ApiErrorResponse


class ErrorMapper:
    """
    Uygulama genelindeki istisnaları standart ApiErrorResponse modeline dönüştürür.

    FastAPI exception handler'larından çağrılır; HTTP durum kodu ile birlikte
    tutarlı bir hata yapısı döner. Bilinmeyen istisnalar 500 INTERNAL_ERROR
    olarak map'lenir.
    """

    @staticmethod
    def to_api_error(exc: Exception) -> tuple[int, ApiErrorResponse]:
        """
        Verilen istisnayı (HTTP status kodu, ApiErrorResponse) tuple'ına dönüştürür.

        Desteklenen istisna türleri:
          - RequestValidationError → 422, hata alanları detay olarak listelenir.
          - HTTPException          → orijinal status kodu korunur; 400/404/422
                                     için anlamlı error_code atanır.
          - Diğer tüm istisnalar  → 500 INTERNAL_ERROR, exc mesajı eklenir.
        """
        if isinstance(exc, RequestValidationError):
            details = [
                f"{'/'.join(str(p) for p in err.get('loc', []))}: {err.get('msg', 'Invalid')}"
                for err in exc.errors()
            ]
            return 422, ApiErrorResponse(
                error_code="REQUEST_VALIDATION_ERROR",
                message="Request validation failed.",
                details=details,
            )

        if isinstance(exc, HTTPException):
            status_code = int(getattr(exc, "status_code", 500))
            detail: Any = getattr(exc, "detail", None)

            details: list[str] = []
            message = "Request failed."

            if isinstance(detail, str):
                message = detail
            elif isinstance(detail, list):
                details = [str(x) for x in detail]
                message = "Request validation failed." if status_code == 422 else "Request failed."
            elif detail is not None:
                details = [json.dumps(detail, ensure_ascii=False, default=str)]
                message = "Request failed."

            if status_code == 400:
                error_code = "BAD_REQUEST"
            elif status_code == 404:
                error_code = "NOT_FOUND"
            elif status_code == 422:
                error_code = "VALIDATION_ERROR"
            else:
                error_code = f"HTTP_{status_code}"

            return status_code, ApiErrorResponse(
                error_code=error_code,
                message=message,
                details=details,
            )

        return 500, ApiErrorResponse(
            error_code="INTERNAL_ERROR",
            message=str(exc),
            details=[],
        )

