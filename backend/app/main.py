from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.middleware import RequestContextMiddleware
from app.db.session import get_db

settings = get_settings()
app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
def handle_app_error(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
def handle_validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": "请求参数无效",
            "details": exc.errors(),
        },
    )


@app.get("/health/live", tags=["system"])
def health_live():
    return {"status": "ok", "environment": settings.app_env}


def database_ready_response(db: Session):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise AppError("database_unavailable", "数据库尚未就绪", status_code=503) from exc
    return {"status": "ready", "environment": settings.app_env}


@app.get("/health/ready", tags=["system"])
def health_ready(db: Session = Depends(get_db)):
    return database_ready_response(db)


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    return database_ready_response(db)
