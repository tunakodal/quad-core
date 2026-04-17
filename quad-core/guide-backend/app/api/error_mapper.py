from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

from app.schemas.dtos import ApiErrorResponse


class ErrorMapper:
    """
    Maps application-wide exceptions to a standard ApiErrorResponse.

    Called from FastAPI exception handlers; returns an HTTP status code
    alongside a consistent error body. Unknown exceptions map to 500 INTERNAL_ERROR.
    """

    @staticmethod
    def to_api_error(exc: Exception) -> tuple[int, ApiErrorResponse]:
        """
        Converts an exception to an (HTTP status code, ApiErrorResponse) tuple.

        Supported exception types:
          - RequestValidationError -> 422, field errors listed in details.
          - HTTPException          -> original status code preserved; readable
                                      error_code assigned for 400/404/422.
          - All other exceptions   -> 500 INTERNAL_ERROR, exc message included.
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
