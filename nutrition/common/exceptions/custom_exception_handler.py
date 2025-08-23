import logging
from django.core.mail import mail_admins
from django.conf import settings
from django.db import IntegrityError, DatabaseError, OperationalError
from django.core.exceptions import ImproperlyConfigured
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)
from elasticsearch import ConnectionError, NotFoundError, RequestError
from jwt import ExpiredSignatureError, InvalidTokenError

logger = logging.getLogger("nutrition")

# Критические ошибки для email-уведомлений (учитывая модели, сигналы, Elasticsearch и JWT)
CRITICAL_EXCEPTIONS = (
    ConnectionError,
    NotFoundError,
    RequestError,  # Ошибки elasticsearch
    ExpiredSignatureError,
    InvalidTokenError,  # JWT-ошибки из JWTAuthTgUser.py
    IntegrityError,
    DatabaseError,
    OperationalError,  # Ошибки БД из models.py/signals.py
    ImproperlyConfigured,  # ошибка в settings.py при отсутсвии требуемой переменной окружения
)


def custom_exception_handler(exc, context):
    """
    Глобальный обработчик исключений для DRF.
    Логирует ошибки, отправляет email для критических случаев и возвращает унифицированный JSON-ответ.
    """
    # Стандартная обработка DRF
    response = exception_handler(exc, context)

    # Собираем детали для логов и email
    request = context.get("request")
    error_details = {
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
        "view": context.get("view", "Unknown view").__class__.__name__,
        "request_path": request.path if request else "Unknown path",
        "telegram_id": getattr(request.user, "telegram_id", None) if request else None,
        "method": request.method if request else "Unknown method",
        "query_params": request.query_params.dict() if request else {},
        "post_data": (
            request.data
            if request and request.method in ["POST", "PUT", "PATCH"]
            else {}
        ),
    }

    if isinstance(exc, CRITICAL_EXCEPTIONS) and not isinstance(exc, APIException):
        logger.critical(f"CRITICAL ERROR: {error_details}", exc_info=True)
        if not settings.DEBUG:
            mail_admins(
                subject=f"Критическая ошибка в Nutrition Tracker: {error_details['error_type']}",
                message=(
                    f"Ошибка: {error_details['error_message']}\n"
                    f"View: {error_details['view']}\n"
                    f"Путь запроса: {error_details['request_path']}\n"
                    f"Telegram ID: {error_details['telegram_id']}\n"
                    f"Метод: {error_details['method']}\n"
                    f"Параметры запроса: {error_details['query_params']}\n"
                    f"Данные запроса: {error_details['post_data']}\n"
                    f"Полная трассировка: {exc.__traceback__}"
                ),
                fail_silently=True,
            )
    else:
        logger.error(f"API Error: {error_details}", exc_info=True)

    # Формируем кастомный ответ
    if response is None:
        response = Response(
            {
                "error": "Внутренняя ошибка сервера",
                "details": "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.",
                "code": "server_error",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    else:
        error_code = getattr(exc, "default_code", "error")
        details = (
            response.data.get("detail", str(exc))
            if isinstance(response.data, dict)
            else response.data  # Для ValidationError с несколькими ошибками
        )

        if isinstance(exc, AuthenticationFailed):
            error_code = "authentication_failed"
            details = "Ошибка аутентификации. Проверьте токен или авторизуйтесь заново."
        elif isinstance(exc, PermissionDenied):
            error_code = "permission_denied"
            details = "Доступ запрещён. Объект не принадлежит вам."
        elif isinstance(exc, ValidationError):
            error_code = "validation_error"
            details = (
                details
                if isinstance(details, dict)
                else "Некорректные данные. Проверьте значения БЖУ, даты, источники данных или права доступа."
            )
        elif isinstance(exc, IntegrityError):
            error_code = "integrity_error"
            details = "Нарушение уникальности или ограничений данных (например, дубль имени продукта)."
        elif isinstance(exc, DatabaseError) or isinstance(exc, OperationalError):
            error_code = "database_error"
            details = "Ошибка базы данных. Пожалуйста, попробуйте позже."
        elif isinstance(exc, ConnectionError):
            error_code = "search_service_unavailable"
            details = "Сервис поиска временно недоступен."
        elif isinstance(exc, NotFoundError):
            error_code = "resource_not_found"
            details = "Запрашиваемый ресурс не найден."
        elif isinstance(exc, RequestError):
            error_code = "invalid_search_query"
            details = "Неверный запрос к поисковому сервису."

        response.data = {"error": str(exc), "details": details, "code": error_code}

    return response
