from __future__ import annotations


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers or {}


def bad_request(details: dict[str, str], message: str = "Invalid input") -> ApiError:
    return ApiError(400, "validation_error", message, details)


def not_found(what: str = "Resource") -> ApiError:
    return ApiError(404, "not_found", f"{what} not found")


def conflict(message: str, code: str = "conflict") -> ApiError:
    return ApiError(409, code, message)


def limit_reached(message: str) -> ApiError:
    return ApiError(409, "limit_reached", message)


def error_body(err: ApiError, request_id: str) -> dict:
    error: dict = {"code": err.code, "message": err.message, "requestId": request_id}
    if err.details:
        error["details"] = err.details
    return {"error": error}
