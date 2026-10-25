import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from payment_api.exceptions import PaymentNotFound

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Настраивает обработчики доменных и неожиданных исключений
    """

    @app.exception_handler(PaymentNotFound)
    async def payment_not_found_handler(
        request: Request, exc: PaymentNotFound
    ) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        msg = (
            f"Unhandled {exc.__class__.__name__} in API endpoint\n"
            f"API endpoint: {request.url.path}\n"
            f"Method: {request.method}"
        )
        request.state._exception_handled = True

        logger.exception(msg)

        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": exc.__class__.__name__,
            },
        )
