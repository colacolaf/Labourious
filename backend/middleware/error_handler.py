import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("labourious")


class LabouriousError(Exception):
    pass


class VaultError(LabouriousError):
    pass


class BrokerError(LabouriousError):
    pass


class DatabaseError(LabouriousError):
    pass


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LabouriousError)
    async def labourious_error_handler(request: Request, exc: LabouriousError):
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": str(exc),
                "code": exc.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
