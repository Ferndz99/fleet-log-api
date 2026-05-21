"""
Custom exception handler con formato RFC 9457.
Versión mejorada con soporte multi-BD, límites de recursión, y mejor logging.
"""

import logging
import re
from typing import Optional, Dict, List, Tuple, Any

from django.db import IntegrityError, connection
from django.http import Http404
from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    ObjectDoesNotExist,
)
from django.db.models.deletion import ProtectedError
from django.utils.translation import gettext_lazy as _
from django.utils.functional import Promise


from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework.utils.serializer_helpers import ReturnList
from rest_framework.exceptions import (
    ValidationError,
    AuthenticationFailed,
    PermissionDenied,
    NotFound,
    MethodNotAllowed,
    NotAuthenticated,
    Throttled,
    ParseError,
)


from psycopg import errors as pg_errors

from apps.common.domain.exceptions import DomainError


logger = logging.getLogger("app")


EXCLUDED_FIELDS = {"company_id"}


def build_rfc9457_error(
    status_code: int,
    title: str | Promise,
    instance: str,
    detail: Optional[str | Promise] = None,
    code: Optional[str] = None,
    errors: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Construye un error compatible con RFC 9457.

    Args:
        status_code: Código HTTP (400, 404, 500, etc.)
        title: Título breve del error
        instance: URI de la petición que causó el error
        detail: Explicación detallada (opcional)
        errors: Lista de errores específicos por campo (opcional)

    Returns:
        Diccionario con estructura RFC 9457
    """
    response = {
        "type": f"https://httpstatuses.com/{status_code}",
        "status": status_code,
        "title": str(title),  # Convertir lazy translation
        "instance": instance,
    }

    if detail is not None:
        response["detail"] = str(detail)  # Convertir lazy translation

    if errors is not None:
        response["errors"] = errors

    if code is not None:
        response["code"] = code

    return response


def flatten_errors(
    data: Any, parent: str = "", max_depth: int = 10, _depth: int = 0
) -> List[Dict[str, str]]:
    """
    Aplana errores anidados de DRF en una lista plana.

    Maneja:
    - Diccionarios anidados
    - Listas de errores
    - Strings individuales

    Args:
        data: Datos a aplanar (dict, list, str)
        parent: Prefijo del campo padre
        max_depth: Profundidad máxima de recursión
        _depth: Profundidad actual (uso interno)

    Returns:
        Lista de diccionarios con 'field' y 'message'

    Example:
        >>> data = {'email': ['Invalid email'], 'nested': {'field': ['Error']}}
        >>> flatten_errors(data)
        [
            {'field': 'email', 'message': 'Invalid email'},
            {'field': 'nested.field', 'message': 'Error'}
        ]
    """

    # Protección contra recursión infinita
    if _depth > max_depth:
        return [
            {
                "field": parent or "non_field_errors",
                "message": str(_("Structure too deep, cannot flatten errors")),
            }
        ]

    flat = []

    if isinstance(data, dict):
        for field, value in data.items():
            full_field = f"{parent}.{field}" if parent else field
            flat.extend(flatten_errors(value, full_field, max_depth, _depth + 1))

    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                flat.extend(flatten_errors(item, parent, max_depth, _depth + 1))
            else:
                flat.append(
                    {
                        "field": parent or "non_field_errors",
                        "message": str(item),
                    }
                )

    else:
        flat.append(
            {
                "field": parent or "non_field_errors",
                "message": str(data),
            }
        )

    return flat


def parse_integrity_error(exc: IntegrityError) -> Tuple[str, List[Dict[str, str]]]:
    """
    Parsea IntegrityError de múltiples motores de BD.
    Usa detección nativa de PostgreSQL cuando es posible.
    """

    msg = str(exc)
    vendor = connection.vendor
    cause = getattr(exc, "__cause__", None)

    # ================================================================
    # DJANGO PROTECTED ERROR
    # ================================================================
    if isinstance(exc, ProtectedError):
        protected_objects = list(exc.protected_objects)

        errors = [
            {
                "field": "non_field_errors",
                "message": str(
                    _("This object is referenced by '%(object)s'.")
                    % {"object": str(obj)}
                ),
            }
            for obj in protected_objects
        ]

        return (
            str(_("Cannot delete object because other resources depend on it.")),
            errors,
        )

    # ================================================================
    # POSTGRESQL UNIQUE (USANDO psycopg2.errors)
    # ================================================================
    if vendor == "postgresql" and isinstance(cause, pg_errors.UniqueViolation):
        # Ejemplo:
        # Key (company_id, sku)=(1, lap123123) already exists.
        match = re.search(r"Key \((.*?)\)=\((.*?)\)", msg)

        if match:
            fields = match.group(1).split(", ")

            structured_errors = [
                {
                    "field": field,
                    "message": str(
                        _("A record with this %(field)s already exists.")
                        % {"field": field}
                    ),
                }
                for field in fields
                if field not in EXCLUDED_FIELDS
            ]

            return (
                str(_("Unique constraint violation.")),
                structured_errors,
            )

        # fallback seguro si no se puede parsear
        return (
            str(_("Unique constraint violation.")),
            [{"field": "non_field_errors", "message": msg}],
        )

    # ================================================================
    # POSTGRESQL FOREIGN KEY
    # ================================================================
    if vendor == "postgresql" and isinstance(cause, pg_errors.ForeignKeyViolation):
        return (
            str(_("Foreign key constraint violation.")),
            [
                {
                    "field": "non_field_errors",
                    "message": str(_("Referenced object does not exist.")),
                }
            ],
        )

    # ================================================================
    # POSTGRESQL NOT NULL
    # ================================================================
    if vendor == "postgresql" and isinstance(cause, pg_errors.NotNullViolation):
        match = re.search(r'null value in column "(\w+)"', msg)
        field = match.group(1) if match else "unknown"

        return (
            str(_("Required field missing.")),
            [
                {
                    "field": field,
                    "message": str(_("This field is required.")),
                }
            ],
        )

    # ================================================================
    # MYSQL / SQLITE (fallback basado en texto)
    # ================================================================
    if vendor == "mysql" and "Duplicate entry" in msg:
        match = re.search(r"for key '(?:\w+\.)?(\w+)'", msg)
        field = match.group(1) if match else "unknown"

        return (
            str(_("Unique constraint violation.")),
            [
                {
                    "field": field,
                    "message": str(
                        _("A record with this %(field)s already exists.")
                        % {"field": field}
                    ),
                }
            ],
        )

    if vendor == "sqlite" and "UNIQUE constraint failed" in msg:
        match = re.search(r"UNIQUE constraint failed: \w+\.(\w+)", msg)
        field = match.group(1) if match else "unknown"

        return (
            str(_("Unique constraint violation.")),
            [
                {
                    "field": field,
                    "message": str(
                        _("A record with this %(field)s already exists.")
                        % {"field": field}
                    ),
                }
            ],
        )

    # ================================================================
    # FALLBACK
    # ================================================================
    return (
        str(_("Database integrity error.")),
        [{"field": "non_field_errors", "message": msg}],
    )


def RFC9457_exception_handler(exc: Exception, context: dict) -> Optional[Response]:
    """
    Manejador de excepciones compatible con RFC 9457.

    Args:
        exc: La excepción lanzada
        context: Contexto de la vista (incluye request, view, etc.)

    Returns:
        Response con formato RFC 9457 o None
    """

    # Logging mejorado
    request = context.get("request")
    instance = request.path if request else "unknown"

    logger.error(
        f"Exception in {instance}: {exc.__class__.__name__}",
        exc_info=True,
        extra={
            "exception_type": exc.__class__.__name__,
            "path": instance,
            "method": request.method if request else None,
            "user": getattr(request.user, "id", None)
            if request and hasattr(request, "user")
            else None,
        },
    )

    response = exception_handler(exc, context)

    # ================================================================
    # CASO A: Excepciones que DRF NO maneja (response es None)
    # ================================================================
    if response is None:
        return _handle_unmanaged_exceptions(exc, instance)

    # ================================================================
    # CASO B: Excepciones manejadas por DRF (response existe)
    # ================================================================
    return _handle_drf_exceptions(exc, context, response)


def _handle_unmanaged_exceptions(exc: Exception, instance: str) -> Response:
    """Maneja excepciones que DRF no procesa por defecto."""

    # Django ValidationError (models/forms)
    if isinstance(exc, DjangoValidationError):
        errors = []

        if hasattr(exc, "message_dict"):
            for field, msgs in exc.message_dict.items():
                for msg in msgs:
                    errors.append({"field": field, "message": msg})
        else:
            for msg in exc.messages:
                errors.append({"field": "non_field_errors", "message": msg})

        data = build_rfc9457_error(
            status_code=400,
            title=_("Validation Error"),
            instance=instance,
            detail=_("The submitted data failed validation."),
            code="validation_error",
            errors=errors,
        )

        return Response(data, status=400, content_type="application/problem+json")

    # IntegrityError (SQL)
    if isinstance(exc, IntegrityError):
        detail, errors = parse_integrity_error(exc)

        data = build_rfc9457_error(
            status_code=400,
            title=_("Bad Request"),
            instance=instance,
            detail=detail,
            code="integrity_error",
            errors=errors,
        )

        return Response(data, status=400, content_type="application/problem+json")

    # ObjectDoesNotExist
    if isinstance(exc, ObjectDoesNotExist):
        data = build_rfc9457_error(
            status_code=404,
            title=_("Not Found"),
            instance=instance,
            detail=_("The requested resource does not exist."),
            code="object_not_found",
        )
        return Response(data, status=404, content_type="application/problem+json")

    # ParseError (JSON inválido)
    if isinstance(exc, ParseError):
        data = build_rfc9457_error(
            status_code=400,
            title=_("Malformed Request"),
            instance=instance,
            detail=_("Malformed JSON or request body."),
            code="parse_error",
        )
        return Response(data, status=400, content_type="application/problem+json")

    if isinstance(exc, DomainError):
        data = build_rfc9457_error(
            status_code=exc.status_code,
            title=_(exc.title),
            instance=instance,
            detail=_(exc.detail),
            code=exc.code,
            errors=exc.errors,
        )

        return Response(
            data,
            status=exc.status_code,
            content_type="application/problem+json",
        )

    # ERROR 500 fallback
    logger.critical(
        f"Unhandled exception: {exc.__class__.__name__}",
        exc_info=True,
        extra={"instance": instance},
    )

    data = build_rfc9457_error(
        status_code=500,
        title=_("Internal Server Error"),
        instance=instance,
        detail=_("An unexpected error occurred. Please try again later."),
        code="internal_server_error",
    )
    return Response(data, status=500, content_type="application/problem+json")


def _handle_drf_exceptions(
    exc: Exception, context: dict, response: Response
) -> Response:
    """Maneja excepciones procesadas por DRF."""

    request = context.get("request")
    instance = request.path if request else "unknown"
    status_code = response.status_code
    status_text = response.status_text
    data_original = response.data

    # Manejo de listas (errores bulk o serializadores anidados)
    if isinstance(data_original, (list, ReturnList)):
        # Verificar si es realmente un error de validación
        if all(isinstance(item, dict) for item in data_original):
            data = build_rfc9457_error(
                status_code=400,
                title=_("Validation Error"),
                instance=instance,
                detail=_("One or more items failed validation."),
                errors=data_original,
            )
            return Response(
                data,
                status=400,
                content_type="application/problem+json",
            )

    # ================================================================
    # CASO NORMAL (dict)
    # ================================================================
    data_original = data_original or {}

    # Unificar extracción de detail
    detail = data_original.get("detail", None)  # type: ignore
    if isinstance(detail, list):
        detail = detail[0] if detail else None

    # Http404 / NotFound
    if isinstance(exc, (Http404, NotFound)):
        data = build_rfc9457_error(
            status_code=404,
            title=_("Not Found"),
            instance=instance,
            detail=detail or _("The requested resource was not found."),
            code="not_found",
        )
        return Response(data, status=404, content_type="application/problem+json")

    # AuthenticationFailed / NotAuthenticated
    # IMPORTANTE: AuthenticationFailed SIEMPRE retorna 401 (estándar HTTP RFC 9110).
    # DRF puede cambiar esto a 403 con AllowAny, pero lo forzamos a 401.
    # Si necesitas 403, usa PermissionDenied en su lugar.
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        data = build_rfc9457_error(
            status_code=401,  # Forzado a 401, ignorando status_code de DRF
            title=_("Unauthorized"),
            instance=instance,
            detail=detail
            or _("Authentication credentials were not provided or are invalid."),
            code="authentication_error",
        )
        return Response(data, status=401, content_type="application/problem+json")

    # PermissionDenied
    if isinstance(exc, PermissionDenied):
        data = build_rfc9457_error(
            status_code=403,
            title=_("Forbidden"),
            instance=instance,
            detail=detail or _("You do not have permission to perform this action."),
            code="permission_denied",
        )
        return Response(data, status=403, content_type="application/problem+json")

    # MethodNotAllowed
    if isinstance(exc, MethodNotAllowed):
        data = build_rfc9457_error(
            status_code=405,
            title=_("Method Not Allowed"),
            instance=instance,
            detail=_("Method '%(method)s' not allowed.") % {"method": request.method}
            if request
            else _("Method not allowed."),
            code="method_not_allowed",
        )
        return Response(data, status=405, content_type="application/problem+json")

    # Throttled
    if isinstance(exc, Throttled):
        wait = exc.wait
        if wait:
            detail = _(
                "Request was throttled. Expected available in %(wait)s seconds."
            ) % {"wait": int(wait)}
        else:
            detail = _("Too many requests.")

        data = build_rfc9457_error(
            status_code=429,
            title=_("Too Many Requests"),
            instance=instance,
            detail=detail,
            code="throttled",
        )
        return Response(data, status=429, content_type="application/problem+json")

    # ValidationError (DRF)
    if isinstance(exc, ValidationError):
        errors = flatten_errors(data_original)

        # Caso especial: un solo error no relacionado a campo
        if len(errors) == 1 and errors[0]["field"] in ("error", "non_field_errors"):
            detail_message = errors[0]["message"]

            data = build_rfc9457_error(
                status_code=400,
                title=_("Validation Error"),
                instance=instance,
                detail=detail_message,
                code="validation_error",
            )

            return Response(
                data,
                status=400,
                content_type="application/problem+json",
            )

        data = build_rfc9457_error(
            status_code=400,
            title=_("Validation Error"),
            instance=instance,
            detail=_("The submitted data failed validation."),
            code="validation_error",
            errors=errors,
        )
        return Response(data, status=400, content_type="application/problem+json")

    # Errores genéricos basados en data
    errors = flatten_errors(data_original) if isinstance(data_original, dict) else None

    data = build_rfc9457_error(
        status_code=status_code,
        title=status_text,
        instance=instance,
        detail=detail,
        code="unhandled_error",
        errors=errors,
    )

    return Response(data, status=status_code, content_type="application/problem+json")
