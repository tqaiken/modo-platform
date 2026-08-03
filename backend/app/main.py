from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    auth,
    export,
    learning_objectives,
    media,
    questions,
    subjects,
    variants,
)
from app.core.config import get_settings


settings = get_settings()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Авторизация и пользователи
app.include_router(
    auth.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Auth"],
)


# Варианты
app.include_router(
    variants.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Variants"],
)


# Вопросы
app.include_router(
    questions.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Questions"],
)


# Предметы
app.include_router(
    subjects.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Subjects"],
)


# Ожидаемые результаты обучения, ОРО
app.include_router(
    learning_objectives.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Learning Objectives"],
)


# Медиафайлы
app.include_router(
    media.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Media"],
)


# Экспорт
app.include_router(
    export.router,
    prefix=settings.API_V1_PREFIX,
    tags=["Export"],
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }