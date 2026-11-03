from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def error_body(code: str, message: str):
    return {"error": {"code": code, "message": message}}


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "服务器内部错误"))
