from fastapi import Request
from fastapi.responses import JSONResponse

class DomainException(Exception):
    """Бизнес-исключение для ошибок валидации (например, неверный ИНН)."""
    def __init__(self, message: str):
        self.message = message

async def domain_exception_handler(request: Request, exc: DomainException):
    """Обработчик, который FastAPI вызовет при DomainException."""
    return JSONResponse(
        status_code=400,
        content={"error": exc.message}
    )